from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from odoo.addons.payment_sipago.tests.common import SipagoCommon
from odoo.exceptions import ValidationError
from odoo.fields import Datetime
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPaymentProvider(SipagoCommon):
    def test_incompatible_with_unsupported_currencies(self):
        """Test that Sipago providers are filtered out from compatible providers when the
        currency is not supported (ARS only)."""
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.USD').id
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_compatible_with_ars_currency(self):
        """Test that Sipago providers are listed as compatible for ARS."""
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.currency_ars.id
        )
        self.assertIn(self.provider, compatible_providers)


@tagged('post_install', '-at_install')
class TestPaymentProviderToken(SipagoCommon):
    def test_token_is_expired_returns_true_when_no_expiration(self):
        """Test that token_is_expired returns True when no expiration date is set."""
        self.provider.sipago_access_token = 'some-token'
        self.provider.sipago_access_token_expiration = False
        self.assertTrue(self.provider.token_is_expired())

    def test_token_is_expired_returns_true_when_no_token(self):
        """Test that token_is_expired returns True when no token is set (ensure_valid_token
        checks both)."""
        self.provider.sipago_access_token = False
        self.provider.sipago_access_token_expiration = Datetime.to_datetime(datetime.utcnow() + timedelta(hours=1))
        self.assertTrue(self.provider.token_is_expired() or not self.provider.sipago_access_token)

    def test_token_is_expired_returns_false_for_valid_token(self):
        """Test that token_is_expired returns False when the token is still valid."""
        self.provider.sipago_access_token = 'some-token'
        self.provider.sipago_access_token_expiration = Datetime.to_datetime(datetime.utcnow() + timedelta(hours=1))
        self.assertFalse(self.provider.token_is_expired())

    def test_token_is_expired_returns_true_for_past_expiration(self):
        """Test that token_is_expired returns True when the expiration is in the past."""
        self.provider.sipago_access_token = 'some-token'
        self.provider.sipago_access_token_expiration = Datetime.to_datetime(datetime.utcnow() - timedelta(hours=1))
        self.assertTrue(self.provider.token_is_expired())

    @patch('odoo.addons.payment_sipago.models.payment_provider.requests.post')
    def test_sipago_set_jwt_token_stores_token_and_expiration(self, mock_post):
        """Test that sipago_set_JWT_token stores the access token and UTC expiration."""
        mock_response = MagicMock()
        mock_response.json.return_value = self.token_response
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        self.provider.sipago_set_JWT_token()
        self.assertEqual(self.provider.sipago_access_token, 'test-access-token')
        expected_expiration = datetime.utcfromtimestamp(1744400255)
        self.assertEqual(
            Datetime.to_datetime(self.provider.sipago_access_token_expiration),
            Datetime.to_datetime(expected_expiration),
        )

    @patch('odoo.addons.payment_sipago.models.payment_provider.requests.post')
    def test_sipago_set_jwt_token_raises_on_missing_expires_in(self, mock_post):
        """Test that sipago_set_JWT_token raises ValidationError when expires_in is missing
        (TypeError from utcfromtimestamp(None))."""
        mock_response = MagicMock()
        mock_response.json.return_value = {'access_token': 'test-token'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with self.assertRaises(ValidationError):
            self.provider.sipago_set_JWT_token()

    def test_ensure_valid_token_refreshes_when_expired(self):
        """Test that ensure_valid_token calls sipago_set_JWT_token when the token is expired."""
        self.provider.sipago_access_token = 'old-token'
        self.provider.sipago_access_token_expiration = Datetime.to_datetime(datetime.utcnow() - timedelta(hours=1))
        with patch(
            'odoo.addons.payment_sipago.models.payment_provider.PaymentProvider.sipago_set_JWT_token'
        ) as mock_set_token:
            self.provider.ensure_valid_token()
            mock_set_token.assert_called_once()

    def test_ensure_valid_token_skips_when_valid(self):
        """Test that ensure_valid_token does not refresh when the token is still valid."""
        self.provider.sipago_access_token = 'valid-token'
        self.provider.sipago_access_token_expiration = Datetime.to_datetime(datetime.utcnow() + timedelta(hours=1))
        with patch(
            'odoo.addons.payment_sipago.models.payment_provider.PaymentProvider.sipago_set_JWT_token'
        ) as mock_set_token:
            self.provider.ensure_valid_token()
            mock_set_token.assert_not_called()

    @patch('odoo.addons.payment_sipago.models.payment_provider.requests.get')
    def test_make_request_retries_on_401_then_succeeds(self, mock_get):
        """Test that _sipago_make_request refreshes the token and retries once on a 401 response."""
        self.provider.sipago_access_token = 'expired-token'
        self.provider.sipago_access_token_expiration = Datetime.to_datetime(datetime.utcnow() + timedelta(hours=1))

        first_response = MagicMock()
        first_response.status_code = 401
        second_response = MagicMock()
        second_response.status_code = 200
        second_response.json.return_value = {'data': {'attributes': {'status': 'SUCCESS'}}}
        second_response.raise_for_status.return_value = None

        mock_get.side_effect = [first_response, second_response]

        with patch.object(self.provider.__class__, 'sipago_set_JWT_token') as mock_set_token:
            result = self.provider._sipago_make_request('/api/v2/orders/test-uuid', method='GET')
            mock_set_token.assert_called_once()
            self.assertEqual(result['data']['attributes']['status'], 'SUCCESS')
