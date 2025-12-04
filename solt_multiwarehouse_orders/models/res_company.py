# -*- coding: utf-8 -*-

from odoo import api, exceptions, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    use_sale_multi_stock = fields.Boolean(string='Use multi warehouse in Sales Orders', readonly=False,)