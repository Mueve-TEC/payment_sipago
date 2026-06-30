from unittest.mock import patch

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.addons.payment_sipago.controllers.main import SipagoController
from odoo.addons.payment_sipago.tests.common import SipagoCommon


@tagged('post_install', '-at_install')
class TestProcessingFlows(SipagoCommon, PaymentHttpCommon):

    @mute_logger('odoo.addons.payment_sipago.controllers.main')
    def test_redirect_notification_triggers_processing(self):
        """ Test that receiving a redirect notification triggers the processing of the notification
        data. """
        self._create_transaction(flow='redirect')
        url = self._build_url(SipagoController._return_url)
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_http_get_request(url, params={
                'ref': self.reference,
                'status': 'APPROVED',
            })
        self.assertEqual(handle_notification_data_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_sipago.controllers.main')
    def test_webhook_notification_triggers_processing(self):
        """ Test that receiving a valid webhook notification triggers the processing of the
        notification data. """
        tx = self._create_transaction(flow='redirect')
        url = self._build_url(f'{SipagoController._webhook_url}/{tx.reference}')
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_json_request(url, data=self.webhook_notification_data)
        self.assertEqual(handle_notification_data_mock.call_count, 1)

    @mute_logger('odoo.addons.payment_sipago.controllers.main')
    def test_webhook_with_non_payment_type_does_not_trigger_processing(self):
        """ Test that a webhook notification with a non-Payment type does not trigger processing. """
        tx = self._create_transaction(flow='redirect')
        url = self._build_url(f'{SipagoController._webhook_url}/{tx.reference}')
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_json_request(url, data={'data': {'type': 'Other'}})
        self.assertEqual(handle_notification_data_mock.call_count, 0)

    @mute_logger('odoo.addons.payment_sipago.controllers.main')
    def test_redirect_without_reference_does_not_trigger_processing(self):
        """ Test that a redirect notification without a reference does not trigger processing. """
        self._create_transaction(flow='redirect')
        url = self._build_url(SipagoController._return_url)
        with patch(
            'odoo.addons.payment.models.payment_transaction.PaymentTransaction'
            '._handle_notification_data'
        ) as handle_notification_data_mock:
            self._make_http_get_request(url, params={'status': 'APPROVED'})
        self.assertEqual(handle_notification_data_mock.call_count, 0)
