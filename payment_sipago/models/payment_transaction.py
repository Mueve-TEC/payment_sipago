
import logging
import pprint
from urllib.parse import quote as url_quote

from werkzeug import urls

from odoo import _, api, models, fields
from odoo.exceptions import UserError, ValidationError

from odoo.addons.payment_sipago.const import ERROR_MESSAGE_MAPPING, TRANSACTION_STATUS_MAPPING
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
            _logger.info(f"\nREFERENCE: {tx.reference} \n")
            order_name = tx.reference.split('-')[0]

            tx.sale_order = tx.env['sale.order'].search([
                ('name', '=', order_name)
            ], limit=1)
            _logger.info(f"\nORDER: {tx.sale_order} \n")

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
        api_url = self.provider_id._sipago_make_request(
            '/api/v2/orders', payload=payload
        )["data"]["attributes"]["links"]["checkout"]

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
    # TODO: implement webhook
    #     base_url = self.provider_id.get_base_url()
    #     return_url = urls.url_join(base_url, SipagoController._return_url)
    #     sanitized_reference = url_quote(self.reference)
    #     webhook_url = urls.url_join(
    #         base_url, f'{SipagoController._webhook_url}/{sanitized_reference}'
    #     )  # Append the reference to identify the transaction from the webhook notification data.

        return {
            "data": {
                "attributes": {
                    # harcoded data
                    "redirect_urls": {
                        "success": "https://dominio.com/?ref=ok",
                        "failed": "https://dominio.com/?ref=fallo"
                    },
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

    # def _get_tx_from_notification_data(self, provider_code, notification_data):
    #     """ Override of `payment` to find the transaction based on Sipago data.

    #     :param str provider_code: The code of the provider that handled the transaction.
    #     :param dict notification_data: The notification data sent by the provider.
    #     :return: The transaction if found.
    #     :rtype: recordset of `payment.transaction`
    #     :raise ValidationError: If inconsistent data were received.
    #     :raise ValidationError: If the data match no transaction.
    #     """
    #     tx = super()._get_tx_from_notification_data(provider_code, notification_data)
    #     if provider_code != 'sipago' or len(tx) == 1:
    #         return tx

    #     reference = notification_data.get('external_reference')
    #     if not reference:
    #         raise ValidationError(
    #             "Sipago: " + _("Received data with missing reference."))

    #     tx = self.search([('reference', '=', reference),
    #                      ('provider_code', '=', 'sipago')])
    #     if not tx:
    #         raise ValidationError(
    #             "Sipago: " +
    #             _("No transaction found matching reference %s.", reference)
    #         )
    #     return tx

    # def _process_notification_data(self, notification_data):
    #     """ Override of `payment` to process the transaction based on Sipago data.

    #     Note: self.ensure_one() from `_process_notification_data`

    #     :param dict notification_data: The notification data sent by the provider.
    #     :return: None
    #     :raise ValidationError: If inconsistent data were received.
    #     """
    #     super()._process_notification_data(notification_data)
    #     if self.provider_code != 'sipago':
    #         return

    #     payment_id = notification_data.get('payment_id')
    #     if not payment_id:
    #         raise ValidationError(
    #             "Sipago: " + _("Received data with missing payment id."))
    #     self.provider_reference = payment_id

    #     # Verify the notification data.
    #     verified_payment_data = self.provider_id._sipago_make_request(
    #         f'/v1/payments/{self.provider_reference}', method='GET'
    #     )

    #     payment_status = verified_payment_data.get('status')
    #     if not payment_status:
    #         raise ValidationError(
    #             "Sipago: " + _("Received data with missing status."))

    #     if payment_status in TRANSACTION_STATUS_MAPPING['pending']:
    #         self._set_pending()
    #     elif payment_status in TRANSACTION_STATUS_MAPPING['done']:
    #         self._set_done()
    #     elif payment_status in TRANSACTION_STATUS_MAPPING['canceled']:
    #         self._set_canceled()
    #     elif payment_status in TRANSACTION_STATUS_MAPPING['error']:
    #         status_detail = verified_payment_data.get('status_detail')
    #         _logger.warning(
    #             "Received data for transaction with reference %s with status %s and error code: %s",
    #             self.reference, payment_status, status_detail
    #         )
    #         error_message = self._sipago_get_error_msg(status_detail)
    #         self._set_error(error_message)
    #     else:  # Classify unsupported payment status as the `error` tx state.
    #         _logger.warning(
    #             "Received data for transaction with reference %s with invalid payment status: %s",
    #             self.reference, payment_status
    #         )
    #         self._set_error(
    #             "Sipago: " +
    #             _("Received data with invalid status: %s", payment_status)
    #         )

    # @api.model
    # def _sipago_get_error_msg(self, status_detail):
    #     """ Return the error message corresponding to the payment status.

    #     :param str status_detail: The status details sent by the provider.
    #     :return: The error message.
    #     :rtype: str
    #     """
    #     return "Sipago: " + ERROR_MESSAGE_MAPPING.get(
    #         status_detail, ERROR_MESSAGE_MAPPING['cc_rejected_other_reason']
    #     )
