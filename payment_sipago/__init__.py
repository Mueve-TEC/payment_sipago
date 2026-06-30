# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.payment import reset_payment_provider, setup_provider

from . import controllers, models


def post_init_hook(cr, registry):
    setup_provider(cr, registry, 'sipago')


def uninstall_hook(cr, registry):
    reset_payment_provider(cr, registry, 'sipago')
