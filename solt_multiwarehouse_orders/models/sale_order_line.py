# -*- coding: utf-8 -*-

from datetime import timedelta
import json
from odoo import fields, models, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warehouse_ids = fields.Many2many('stock.warehouse', compute='_compute_warehouse_ids')
    warehouse_id = fields.Many2one(related='multi_warehouse_id', string='Warehouse', store=True, readonly=True)
    warehouse_id_domain = fields.Char(compute='_compute_warehouse_ids')
    product_type = fields.Selection(related="product_id.type")
    product_is_storable = fields.Boolean(related="product_id.is_storable")
    multi_warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', store=True)

    commitment_date = fields.Datetime("Delivery Date")

    @api.depends('order_id.warehouse_ids')
    def _compute_warehouse_ids(self):
        for line in self:
            line = line.with_company(line.company_id)
            line.warehouse_ids = line.order_id.warehouse_ids
            line.warehouse_id_domain = json.dumps([('id', 'in', line.warehouse_ids.ids)])

    def _prepare_procurement_values(self, group_id=False):
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id=group_id)
        if self.order_id.can_use_sale_multi_stock:
            values.update({'warehouse_id': self.warehouse_id or False})

            if self.commitment_date:
                values.update(
                    {
                        "date_planned": self.commitment_date
                        - timedelta(days=self.order_id.company_id.security_lead),
                        "date_deadline": self.commitment_date,
                    }
                )
        if not self.order_id.can_use_sale_multi_stock:
            values.update({'warehouse_id': self.order_id.warehouse_id or False})
        return values

    # propagate commitment_date on moves
    def write(self, vals):
        res = super().write(vals)
        if self.env.company.use_sale_multi_stock:
            moves_to_update = set()
            if "commitment_date" in vals:
                for line in self:
                    for move in line.move_ids:
                        if move.state not in ["cancel", "done"]:
                            moves_to_update.add(move.id)
            if moves_to_update:
                self.env["stock.move"].browse(moves_to_update).write(
                    {"date_deadline": vals.get("commitment_date")}
                )
        return res