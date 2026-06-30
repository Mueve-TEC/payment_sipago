from unittest.mock import patch
from urllib.parse import quote as url_quote

from werkzeug import urls

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_sipago.controllers.main import SipagoController
from odoo.addons.payment_sipago.tests.common import SipagoCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestPaymentTransaction(SipagoCommon, PaymentHttpCommon):
    def test_no_item_missing_from_preference_request_payload(self):
        """Test that the request values are conform to the transaction fields."""
        tx = self._create_transaction(flow='redirect')
        request_payload = tx._sipago_prepare_preference_request_payload()
        self.maxDiff = 10000

        base_url = tx.provider_id.get_base_url()
        if base_url.startswith('http://'):
            base_url = base_url.replace('http://', 'https://', 1)
        sanitized_reference = url_quote(tx.reference)
        webhook_url = urls.url_join(base_url, f'{SipagoController._webhook_url}/{sanitized_reference}')
        success_url = urls.url_join(
            base_url, f'{SipagoController._return_url}?ref={sanitized_reference}&status=APPROVED'
        )
        failed_url = urls.url_join(base_url, f'{SipagoController._return_url}?ref={sanitized_reference}&status=DENIED')
        amount = round(tx.amount * 100)

        self.assertDictEqual(
            request_payload,
            {
                'data': {
                    'attributes': {
                        'redirect_urls': {
                            'success': success_url,
                            'failed': failed_url,
                        },
                        'webhookUrl': webhook_url,
                        'currency': '032',
                        'items': [
                            {
                                'id': '0',
                                'name': 'Total a pagar',
                                'unitPrice': {
                                    'currency': '032',
                                    'amount': amount,
                                },
                                'quantity': 1,
                            }
                        ],
                    },
                },
            },
        )

    def test_amount_uses_round_not_int(self):
        """Test that the amount in cents is rounded, not truncated (float precision fix)."""
        tx = self._create_transaction(flow='redirect', amount=19.99)
        payload = tx._sipago_prepare_preference_request_payload()
        amount = payload['data']['attributes']['items'][0]['unitPrice']['amount']
        self.assertEqual(amount, 1999)

    @mute_logger('odoo.addons.payment.models.payment_transaction')
    def test_no_input_missing_from_redirect_form(self):
        """Test that the `api_url` key is not omitted from the rendering values."""
        tx = self._create_transaction(flow='redirect')
        with patch(
            'odoo.addons.payment_sipago.models.payment_transaction.PaymentTransaction._get_specific_rendering_values',
            return_value={'api_url': 'https://dummy.com'},
        ):
            processing_values = tx._get_processing_values()
        form_info = self._extract_values_from_html_form(processing_values['redirect_form_html'])
        self.assertEqual(form_info['action'], 'https://dummy.com')
        self.assertEqual(form_info['method'], 'get')
        self.assertDictEqual(form_info['inputs'], {})

    def test_processing_notification_data_confirms_transaction(self):
        """Test that the transaction state is set to 'done' when the notification data indicate a
        successful payment (order SUCCESS + payment APPROVED)."""
        tx = self._create_transaction(flow='redirect', provider_reference=self.order_uuid)
        with patch(
            'odoo.addons.payment_sipago.models.payment_provider.Paymentprovider._sipago_make_request',
            return_value=self.verification_data_success,
        ):
            tx._process_notification_data(self.redirect_notification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_sipago.models.payment_transaction')
    def test_processing_notification_data_sets_pending(self):
        """Test that the transaction state is set to 'pending' when the notification data indicate
        a pending order."""
        tx = self._create_transaction(flow='redirect', provider_reference=self.order_uuid)
        with patch(
            'odoo.addons.payment_sipago.models.payment_provider.Paymentprovider._sipago_make_request',
            return_value=self.verification_data_pending,
        ):
            tx._process_notification_data(self.redirect_notification_data)
        self.assertEqual(tx.state, 'pending')

    @mute_logger('odoo.addons.payment_sipago.models.payment_transaction')
    def test_processing_notification_data_cancels_transaction(self):
        """Test that the transaction state is set to 'cancel' when the notification data indicate
        an expired order."""
        tx = self._create_transaction(flow='redirect', provider_reference=self.order_uuid)
        with patch(
            'odoo.addons.payment_sipago.models.payment_provider.Paymentprovider._sipago_make_request',
            return_value=self.verification_data_expired,
        ):
            tx._process_notification_data(self.redirect_notification_data)
        self.assertEqual(tx.state, 'cancel')

    @mute_logger('odoo.addons.payment_sipago.models.payment_transaction')
    def test_processing_notification_data_rejects_transaction(self):
        """Test that the transaction state is set to 'error' when the notification data indicate
        a failed order."""
        tx = self._create_transaction(flow='redirect', provider_reference=self.order_uuid)
        with patch(
            'odoo.addons.payment_sipago.models.payment_provider.Paymentprovider._sipago_make_request',
            return_value=self.verification_data_failed,
        ):
            tx._process_notification_data(self.redirect_notification_data)
        self.assertEqual(tx.state, 'error')

    def test_processing_notification_data_is_idempotent_when_done(self):
        """Test that processing a second success notification does not change the state."""
        tx = self._create_transaction(flow='redirect', provider_reference=self.order_uuid)
        with patch(
            'odoo.addons.payment_sipago.models.payment_provider.Paymentprovider._sipago_make_request',
            return_value=self.verification_data_success,
        ):
            tx._process_notification_data(self.redirect_notification_data)
        self.assertEqual(tx.state, 'done')
        with patch(
            'odoo.addons.payment_sipago.models.payment_provider.Paymentprovider._sipago_make_request',
            return_value=self.verification_data_success,
        ):
            tx._process_notification_data(self.redirect_notification_data)
        self.assertEqual(tx.state, 'done')

    @mute_logger('odoo.addons.payment_sipago.models.payment_transaction')
    def test_webhook_with_mismatched_uuid_raises_and_skips_api_call(self):
        """Test that a webhook with a mismatched order UUID raises ValidationError and does not
        make an API call (spam prevention)."""
        tx = self._create_transaction(flow='redirect', provider_reference=self.order_uuid)
        webhook_data = {
            'reference': tx.reference,
            'order_uuid': 'fake-uuid-not-matching',
            'source': 'api_checkout',
        }
        with patch(
            'odoo.addons.payment_sipago.models.payment_provider.Paymentprovider._sipago_make_request'
        ) as mock_request:
            with self.assertRaises(ValidationError):
                tx._process_notification_data(webhook_data)
            mock_request.assert_not_called()
