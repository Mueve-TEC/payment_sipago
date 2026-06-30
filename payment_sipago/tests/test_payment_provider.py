from odoo.tests import tagged

from odoo.addons.payment_sipago.tests.common import SipagoCommon


@tagged('post_install', '-at_install')
class TestPaymentProvider(SipagoCommon):

    def test_incompatible_with_unsupported_currencies(self):
        """ Test that Sipago providers are filtered out from compatible providers when the
        currency is not supported (ARS only). """
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.env.ref('base.USD').id
        )
        self.assertNotIn(self.provider, compatible_providers)

    def test_compatible_with_ars_currency(self):
        """ Test that Sipago providers are listed as compatible for ARS. """
        compatible_providers = self.env['payment.provider']._get_compatible_providers(
            self.company_id, self.partner.id, self.amount, currency_id=self.currency_ars.id
        )
        self.assertIn(self.provider, compatible_providers)
