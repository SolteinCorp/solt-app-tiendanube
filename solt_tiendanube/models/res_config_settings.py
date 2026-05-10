# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"
    use_sale_multi_stock = fields.Boolean(string="Use multi warehouse in Sales Orders", readonly=False, related="company_id.use_sale_multi_stock")

    @api.model
    def set_values(self):
        """Persist the multi-warehouse flag on the current company before saving the settings."""
        self.env.company.write({"use_sale_multi_stock": self.use_sale_multi_stock or self.env.company.use_sale_multi_stock})
        return super(ResConfigSettings, self).set_values()
