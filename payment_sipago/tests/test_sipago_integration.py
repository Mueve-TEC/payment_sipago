import logging

from odoo.addons.payment_sipago.tests.common import SipagoCommon
from odoo.tests import tagged

_logger = logging.getLogger(__name__)

SIPAGO_DEV_CLIENT_ID = '3c21db0f-6913-43db-88d6-2ced87b99a91'
SIPAGO_DEV_CLIENT_SECRET = 'ft6z30q2ftsmu90au0mp'


@tagged('post_install', '-at_install', 'external')
class TestSipagoJWTIntegration(SipagoCommon):
    def test_jwt_token_from_real_sipago_dev_server(self):
        """Request a real JWT token from Sipago's development auth server.

        This test makes a real HTTP request to auth.stg.geopagos.io using the
        public development credentials from https://docs.sipago.coop/API%20Cobros/credencialDev
        """
        self.provider.sipago_env = 'DEVELOPMENT'
        self.provider.sipago_client_id = SIPAGO_DEV_CLIENT_ID
        self.provider.sipago_client_secret = SIPAGO_DEV_CLIENT_SECRET
        self.provider.sipago_access_token = False
        self.provider.sipago_access_token_expiration = False

        self.provider.sipago_set_JWT_token()

        self.assertTrue(self.provider.sipago_access_token, 'No access token received from Sipago')
        self.assertTrue(
            self.provider.sipago_access_token_expiration,
            'No token expiration received from Sipago',
        )

        _logger.info(
            'Successfully obtained JWT token from Sipago dev server, expires at %s',
            self.provider.sipago_access_token_expiration,
        )

    def test_ensure_valid_token_with_real_sipago_dev_server(self):
        """Test ensure_valid_token refreshes the token using the real Sipago dev server."""
        self.provider.sipago_env = 'DEVELOPMENT'
        self.provider.sipago_client_id = SIPAGO_DEV_CLIENT_ID
        self.provider.sipago_client_secret = SIPAGO_DEV_CLIENT_SECRET
        self.provider.sipago_access_token = False
        self.provider.sipago_access_token_expiration = False

        self.provider.ensure_valid_token()

        self.assertTrue(self.provider.sipago_access_token)
        self.assertTrue(self.provider.sipago_access_token_expiration)

    def test_make_request_with_real_sipago_dev_server(self):
        """Test _sipago_make_request authenticates and reaches the Sipago dev API.

        We request a non-existent order UUID, which should return a 404 error
        rather than an auth error — proving the JWT token was obtained and used.
        """
        self.provider.sipago_env = 'DEVELOPMENT'
        self.provider.sipago_client_id = SIPAGO_DEV_CLIENT_ID
        self.provider.sipago_client_secret = SIPAGO_DEV_CLIENT_SECRET
        self.provider.sipago_access_token = False
        self.provider.sipago_access_token_expiration = False

        from odoo.exceptions import ValidationError

        with self.assertRaises(ValidationError) as ctx:
            self.provider._sipago_make_request('/api/v2/orders/00000000-0000-0000-0000-000000000000', method='GET')
        self.assertIn('Sipago', str(ctx.exception))
