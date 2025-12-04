# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _get_brand_domain(self):
        domain = [('company_id', '=', False)]
        if self.env.user.has_group('base.group_multi_company'):
            domain = ['|'] + domain + [('company_id', 'parent_of', self.env.company.id)]
        else:
            domain = ['|'] + domain + [('company_id', '=', self.env.company.id)]
        return domain

    product_brand_id = fields.Many2one(
        "solt.product.brand", string="Brand", help="Select a brand for the product",
        domain=lambda self: self._get_brand_domain()
    )