# -*- coding: utf-8 -*-

import logging
from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    fulfillmen_external_id = fields.Char('External shipment ID')

    def _get_warehouse_from_data(self, assigned_location):
        if not isinstance(assigned_location, dict):
            return False

        warehouse_id = self.env['stock.warehouse'].sudo().with_company(self.env.company).search([
            ('x_external_id', '=', assigned_location.get('location_id'))
        ])
        if not warehouse_id:
            _logger.info(
                _(f"Warehouse not found with ID {assigned_location.get('location_id')} for the company {self.env.company.name}"))
        return warehouse_id and warehouse_id.id or False