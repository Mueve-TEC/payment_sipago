
import logging
import pprint
from urllib.parse import quote as url_quote

from werkzeug import urls

from odoo import _, api, models, fields
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment_sipago.const import TRANSACTION_STATUS_MAPPING, ERROR_MESSAGE_MAPPING
from odoo.addons.payment_sipago.controllers.main import SipagoController


_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    sale_order = fields.Many2one(
        comodel_name='sale.order',
        string='Sale Order',
        compute='_compute_sale_order',
        store=False,
    )

    @api.depends('reference')
    def _compute_sale_order(self):
        """ Compute the sale order based on the reference of the transaction.

        Note: This method is not stored in the database.

        :return: None
        """
        for tx in self:
            order_name = tx.reference.split('-')[0]

            tx.sale_order = tx.env['sale.order'].search([
                ('name', '=', order_name)
            ], limit=1)

        if not self.sale_order:
            raise UserError(_(
                "No se ha encontrado la orden de venta asociada a la transacción."
            ))

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
        sanitized_reference = url_quote(self.reference)
        webhook_url = urls.url_join(
            base_url, f'{SipagoController._webhook_url}/{sanitized_reference}'
        )  # Append the reference to identify the transaction from the webhook notification data.        
        
        # TODO : tal vez hacer algo con el status
        success_url = urls.url_join(base_url, f'{SipagoController._return_url}?ref={sanitized_reference}&status=APPROVED')
        failed_url = urls.url_join(base_url, f'{SipagoController._return_url}?ref={sanitized_reference}&status=DENIED')
        

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
                            'amount': int(self.sale_order.amount_total * 100)
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
        
        # if the source is 'return_url', use the existing provider_reference
        # otherwise, use the order_uuid from the notification data
        if notification_data.get('source') == 'return_url':
            url_status = notification_data.get('payment_status')
            _logger.info("Processing Sipago return URL data for transaction %s with status %s", reference, url_status)
            uuid = self.provider_reference
        elif notification_data.get('source'):
            uuid = notification_data.get('order_uuid')
        else:
            raise ValidationError(
                "Sipago: " + _("Could not determine the sipago payment uuid for transaction %s.", reference))
        

        # Verify the notification data.
        verified_payment_data = self.provider_id._sipago_make_request(
            f'/api/v2/orders/{uuid}', method='GET'
        )["data"]["attributes"]

        payment_status = verified_payment_data.get('status')
        if not payment_status:
            raise ValidationError(
                "Sipago: " + _("Received data with missing status."))

        if payment_status in TRANSACTION_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in TRANSACTION_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in TRANSACTION_STATUS_MAPPING['canceled']:
            self._set_canceled()
        elif payment_status in TRANSACTION_STATUS_MAPPING['error']:
            _logger.warning(
                "Received data for transaction with reference %s and status %s and sipago uuid %s",
                reference, payment_status, uuid
            )
            error_message = self._sipago_get_error_msg(payment_status)
            self._set_error(
                "Sipago: " + _("Received data with error status: %s. %s", payment_status, error_message)
            )
        else:  # Classify unsupported payment status as the `error` tx state.
            _logger.warning(
                "Received data for transaction with reference %s with invalid payment status: %s.",
                reference, payment_status
            )
            self._set_error(
                "Sipago: " +
                _("Received data with invalid status: %s", payment_status)
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
