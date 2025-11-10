
import logging
import pprint
from urllib.parse import quote as url_quote

from werkzeug import urls

from odoo import _, api, models, fields
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment_sipago.const import ORDER_STATUS_MAPPING, ERROR_MESSAGE_MAPPING
from odoo.addons.payment_sipago.controllers.main import SipagoController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_rendering_values(self, processing_values):
        """ Override of `payment` to return Sipago-specific rendering values.

        Note: self.ensure_one() from `_get_rendering_values`.

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'sipago':
            return res

        # Initiate the payment and retrieve the payment link data.
        payload = self._sipago_prepare_preference_request_payload()

        _logger.info(
            "Sending /api/v2/orders request for link creation:\n%s",
            pprint.pformat(payload),
        )

        response = self.provider_id._sipago_make_request(
            '/api/v2/orders', payload=payload
        )
        
        # Extract UUID and store it in provider_reference
        order_uuid = response["data"]["attributes"]["uuid"]
        self.provider_reference = order_uuid
        _logger.info("Stored Sipago order UUID %s for transaction %s", order_uuid, self.reference)
        
        api_url = response["data"]["attributes"]["links"]["checkout"]

        # Extract the payment link URL and embed it in the redirect form.
        rendering_values = {
            'api_url': api_url,
        }
        return rendering_values

    def _sipago_prepare_preference_request_payload(self):
        """ Create the payload for the preference request based on the transaction values.

        :return: The request payload.
        :rtype: dict
        """
        base_url = self.provider_id.get_base_url()
        
        # Forzar HTTPS si viene HTTP
        if base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://', 1)
            _logger.warning("Base URL was HTTP, forcing HTTPS: %s", base_url)

        sanitized_reference = url_quote(self.reference)
        webhook_url = urls.url_join(
            base_url, f'{SipagoController._webhook_url}/{sanitized_reference}'
        )  # Append the reference to identify the transaction from the webhook notification data.        
        
        success_url = urls.url_join(base_url, f'{SipagoController._return_url}?ref={sanitized_reference}&status=APPROVED')
        failed_url = urls.url_join(base_url, f'{SipagoController._return_url}?ref={sanitized_reference}&status=DENIED')
        
        amount = int(self.amount * 100)

        return {
            "data": {
                "attributes": {
                    "redirect_urls": {
                        "success": success_url,
                        "failed": failed_url
                    },
                    "webhookUrl": webhook_url,
                    "currency": "032",
                    "items": [{
                        'id': '0',
                        'name': 'Total a pagar',
                        'unitPrice': {
                            'currency': '032',
                            'amount': amount
                        },
                        'quantity': 1
                    }]
                }
            }
        }

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of `payment` to find the transaction based on Sipago data.

        :param str provider_code: The code of the provider that handled the transaction.
        :param dict notification_data: The notification data sent by the provider.
        :return: The transaction if found.
        :rtype: recordset of `payment.transaction`
        :raise ValidationError: If inconsistent data were received.
        :raise ValidationError: If the data match no transaction.
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'sipago' or len(tx) == 1:
            return tx

        reference = notification_data.get('reference')
        if not reference:
            raise ValidationError(
                "Sipago: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference),
                         ('provider_code', '=', 'sipago')])
        if not tx:
            raise ValidationError(
                "Sipago: " +
                _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        """ Override of `payment` to process the transaction based on Sipago data.

        Note: self.ensure_one() from `_process_notification_data`

        :param dict notification_data: The notification data sent by the provider.
        :return: None
        :raise ValidationError: If inconsistent data were received.
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'sipago':
            return

        reference = notification_data.get('reference')
        if not reference:
            raise ValidationError(
                "Sipago: " + _("Processing notification data with missing payment reference."))
        
        # Determine the UUID based on the notification source
        uuid = self._sipago_get_order_uuid(notification_data, reference)
        
        # Verify the notification data
        verified_order_data = self._sipago_fetch_order_data(uuid, reference)
        
        # Extract and validate order status
        order_status = verified_order_data.get('status')
        if not order_status:
            raise ValidationError(
                "Sipago: " + _("Received data with missing order status for transaction %s.", reference))
        
        # Extract and validate payment status
        payment_status, payment_error = self._sipago_extract_payment_info(
            verified_order_data, reference
        )
        
        # Process transaction based on status
        self._sipago_handle_transaction_status(
            order_status, payment_status, payment_error, reference, uuid
        )

    def _sipago_get_order_uuid(self, notification_data, reference):
        """ Extract the order UUID from notification data.
        
        :param dict notification_data: The notification data sent by the provider.
        :param str reference: The transaction reference.
        :return: The order UUID.
        :rtype: str
        :raise ValidationError: If UUID cannot be determined.
        """
        source = notification_data.get('source')
        
        if source == 'return_url':
            url_status = notification_data.get('payment_status')
            _logger.info(
                "Processing Sipago return URL data for transaction %s with status %s",
                reference, url_status
            )
            uuid = self.provider_reference
        elif source:
            uuid = notification_data.get('order_uuid')
        else:
            raise ValidationError(
                "Sipago: " + _("Could not determine the sipago payment uuid for transaction %s.", reference))
        
        if not uuid:
            raise ValidationError(
                "Sipago: " + _("Missing order UUID for transaction %s.", reference))
        
        return uuid

    def _sipago_fetch_order_data(self, uuid, reference):
        """ Fetch and verify order data from Sipago API.
        
        :param str uuid: The order UUID.
        :param str reference: The transaction reference.
        :return: The verified order data.
        :rtype: dict
        """
        verified_order_data = self.provider_id._sipago_make_request(
            f'/api/v2/orders/{uuid}', method='GET'
        )["data"]["attributes"]

        _logger.info(
            "Verified Sipago payment data for transaction %s:\n%s",
            reference, pprint.pformat(verified_order_data)
        )
        
        return verified_order_data

    def _sipago_extract_payment_info(self, verified_order_data, reference):
        """ Extract payment status and error information from order data.
        
        :param dict verified_order_data: The verified order data from Sipago.
        :param str reference: The transaction reference.
        :return: Tuple of (payment_status, payment_error)
        :rtype: tuple
        :raise ValidationError: If payment status is missing.
        """
        payment_data = verified_order_data.get('payment', {})
        payment_error = None
        
        if payment_data:
            payment_status = payment_data.get('status')
        else:
            # Check for failed payments in the payments array
            failed_payments = verified_order_data.get('payments', [])
            if failed_payments: 
                _logger.warning(
                    "No payment data found for transaction %s, but found failed payments: %s",
                    reference, pprint.pformat(failed_payments)
                )
                last_payment = failed_payments[-1]
                payment_status = last_payment.get('status')
                payment_error = last_payment.get('error', {})
            else:
                payment_status = None
        
        if not payment_status:
            raise ValidationError(
                "Sipago: " + _("Received data with missing payment status for transaction %s.", reference))
        
        return payment_status, payment_error

    def _sipago_handle_transaction_status(self, order_status, payment_status, payment_error, reference, uuid):
        """ Handle transaction state based on order and payment status.
        
        :param str order_status: The order status from Sipago.
        :param str payment_status: The payment status.
        :param dict payment_error: Payment error information (if any).
        :param str reference: The transaction reference.
        :param str uuid: The order UUID.
        :return: None
        """
        if order_status in ORDER_STATUS_MAPPING['pending']:
            if payment_status == 'DENIED' and payment_error:
                _logger.info(
                    "Payment was denied for transaction %s: %s - %s",
                    reference,
                    payment_error.get('description'),
                    payment_error.get('message')
                )
            self._set_pending()
            
        elif order_status in ORDER_STATUS_MAPPING['done'] and payment_status == 'APPROVED':
            if self.state != 'done':
                self._set_done()
            else:
                _logger.info(
                    "Transaction %s is already done, no state change needed.", reference
                )
        elif order_status in ORDER_STATUS_MAPPING['canceled']:
            self._set_canceled()
            
        elif order_status in ORDER_STATUS_MAPPING['error']:
            _logger.warning(
                "Received data for transaction with reference %s and status %s and sipago uuid %s",
                reference, order_status, uuid
            )
            error_message = self._sipago_get_error_msg(order_status)
            self._set_error(
                "Sipago: " + _("Received data with error status: %s. %s", order_status, error_message)
            )
            
        else:  # Classify unsupported order status as the `error` tx state
            _logger.warning(
                "Received data for transaction with reference %s with invalid order status: %s.",
                reference, order_status
            )
            self._set_error(
                "Sipago: " + _("Received data with invalid status: %s", order_status)
            )

    @api.model
    def _sipago_get_error_msg(self, status_detail):
        """ Return the error message corresponding to the payment status.

        :param str status_detail: The status details sent by the provider.
        :return: The error message.
        :rtype: str
        """
        return "Sipago: " + ERROR_MESSAGE_MAPPING.get(
            status_detail, ERROR_MESSAGE_MAPPING['cc_rejected_other_reason']
        )
