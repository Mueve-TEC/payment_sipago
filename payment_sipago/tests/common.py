from odoo.addons.payment.tests.common import PaymentCommon


class SipagoCommon(PaymentCommon):
    ORDER_UUID = 'bc39016f-6fad-4ee1-b4c3-5eb8d1db8911'

    @classmethod
    def setUpClass(cls):
        from odoo.modules.registry import Registry
        from odoo.tools.misc import config

        db_name = config['db_name'] or 'admin'
        with Registry(db_name).cursor() as cr:
            cr.execute("UPDATE res_lang SET active = true WHERE code = 'en_US'")
        super().setUpClass()

        cls.currency_ars = cls._prepare_currency('ARS')

        cls.provider = cls._prepare_provider(
            'sipago',
            update_values={
                'sipago_client_id': 'test-client-id',
                'sipago_client_secret': 'test-client-secret',
                'sipago_env': 'DEVELOPMENT',
            },
        )
        cls.currency = cls.currency_ars

        cls.order_uuid = cls.ORDER_UUID

        cls.token_response = {
            'token_type': 'Bearer',
            'expires_in': 1744400255,
            'access_token': 'test-access-token',
        }

        cls.order_creation_response = {
            'data': {
                'attributes': {
                    'uuid': cls.order_uuid,
                    'links': {
                        'checkout': f'https://cabal-checkout.preprod.geopagos.com/orders/{cls.order_uuid}',
                    },
                },
            },
        }

        cls.verification_data_success = {
            'data': {
                'attributes': {
                    'uuid': cls.order_uuid,
                    'status': 'SUCCESS',
                    'payment': {'id': 123, 'status': 'APPROVED'},
                    'payments': None,
                },
            },
        }
        cls.verification_data_pending = {
            'data': {
                'attributes': {
                    'uuid': cls.order_uuid,
                    'status': 'PENDING',
                    'payment': {'id': 456, 'status': 'DENIED'},
                    'payments': None,
                },
            },
        }
        cls.verification_data_expired = {
            'data': {
                'attributes': {
                    'uuid': cls.order_uuid,
                    'status': 'EXPIRED',
                    'payment': None,
                    'payments': [{'id': 789, 'status': 'DENIED', 'error': {}}],
                },
            },
        }
        cls.verification_data_failed = {
            'data': {
                'attributes': {
                    'uuid': cls.order_uuid,
                    'status': 'FAILED',
                    'payment': {'id': 999, 'status': 'DENIED'},
                    'payments': None,
                },
            },
        }

        cls.redirect_notification_data = {
            'reference': cls.reference,
            'payment_status': 'APPROVED',
            'source': 'return_url',
        }
        cls.webhook_notification_data = {
            'data': {
                'type': 'Payment',
                'order': {
                    'uuid': cls.order_uuid,
                    'status': 'SUCCESS',
                    'source': 'api_checkout',
                },
                'payment': {
                    'id': 1823,
                    'authorizationCode': '901159',
                    'refNumber': '62b4a8ff60fee',
                    'status': 'APPROVED',
                },
            },
        }
