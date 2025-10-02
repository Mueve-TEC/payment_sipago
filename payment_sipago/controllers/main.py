# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request


_logger = logging.getLogger(__name__)


class SipagoController(http.Controller):
    _return_url = '/payment/sipago/return'
    _webhook_url = '/payment/sipago/webhook'

    @http.route(_return_url, type='http', methods=['GET'], auth='public')
    def sipago_return_from_checkout(self, **data):
        """ Process the notification data sent by Sipago after redirection from checkout.

        :param dict data: The notification data from Sipago redirect URLs.
        """
        # Handle the notification data.
        _logger.info(
            "Handling redirection from Sipago with data:\n%s", pprint.pformat(data))
        
        # Sipago uses redirect URLs for success/failed scenarios
        # The transaction reference should be passed in the URL parameters
        transaction_reference = data.get('ref')
        
        if transaction_reference:
            # Structure the data similar to webhook format for consistency
            notification_data = {
                'reference': transaction_reference,
                'payment_status': data.get('status'),
                'source': 'return_url' 
            }
            
            request.env['payment.transaction'].sudo()._handle_notification_data(
                'sipago', notification_data
            )
        else:
            _logger.warning("No transaction reference found in Sipago return data")


        # Redirect the user to the status page.
        return request.redirect('/payment/status')

    @http.route(
        f'{_webhook_url}/<reference>', type='http', auth='public', methods=['POST'], csrf=False
    )
    def sipago_webhook(self, reference, **_kwargs):
        """ Process the notification data sent by Sipago to the webhook.

        :param str reference: The transaction reference embedded in the webhook URL.
        :param dict _kwargs: The extra query parameters.
        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info("Webhook notification received from Sipago with data:\n%s", pprint.pformat(data))

        if data and data.get('data', {}).get('type') == 'Payment':
            try:
                sipago_data = data.get('data', {})
                order_data = sipago_data.get('order', {})
                payment_data = sipago_data.get('payment', {})
                
                notification_data = {
                    'reference': reference, 
                    'order_uuid': order_data.get('uuid'),
                    'order_status': order_data.get('status'),
                    'payment_id': payment_data.get('id'),
                    'payment_status': payment_data.get('status'),
                    'authorization_code': payment_data.get('authorizationCode'),
                    'ref_number': payment_data.get('refNumber'),
                    'source': order_data.get('source') 
                }
                
                # Handle the notification data using the payment transaction model
                request.env['payment.transaction'].sudo()._handle_notification_data(
                    'sipago', notification_data
                )
                
            except ValidationError:  # Acknowledge the notification to avoid getting spammed.
                _logger.exception("Unable to handle the notification data; skipping to acknowledge")
            except Exception as e:
                _logger.exception("Error processing Sipago webhook: %s", str(e))
        else:
            _logger.warning("Received Sipago webhook with unexpected structure or missing payment data")
            
        return ''  # Acknowledge the notification.
