
{
    'name': "Payment Provider: Sipago",
    'version': '16.0.1.0.1',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A checkout payment provider for debit and credit cards.",
    'author': "Mueve",
    'website': "https://github.com/Mueve-TEC",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['payment'],
    'data': [
        'views/payment_sipago_templates.xml',
        'views/payment_provider_views.xml',

        'data/payment_provider_data.xml',  # Depends on views/payment_sipago_templates.xml
    ],
    'application': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'license': 'AGPL-3',
}
