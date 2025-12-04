# -*- coding: utf-8 -*-

import logging

from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    can_use_sale_multi_stock = fields.Boolean(compute='_compute_use_sale_multi_stock')
    warehouse_ids = fields.Many2many(
        'stock.warehouse', string='Warehouse', required=False,
        compute='_compute_warehouse_id', store=True, readonly=False, precompute=True,
        check_company=True)

    @api.depends_context('company', 'uid')
    @api.depends('company_id')
    def _compute_use_sale_multi_stock(self):
        for order in self:
            order = order.with_company(order.company_id)
            order.can_use_sale_multi_stock = order.company_id.use_sale_multi_stock or self.env.company.use_sale_multi_stock

    @api.depends('user_id', 'company_id')
    def _compute_warehouse_id(self):
        super(SaleOrder, self)._compute_warehouse_id()
        for order in self:
            if order.warehouse_id and not order.warehouse_ids:
                order.warehouse_ids = [(4, order.warehouse_id.id)]
            else:
                order.warehouse_ids = []

    @api.onchange("commitment_date")
    def _onchange_commitment_date(self):
        """Actualizar líneas de pedido sin la fecha de entrega
        con la fecha de entrega de la orden de venta"""
        result = super()._onchange_commitment_date() or {}
        if "warning" not in result and self.can_use_sale_multi_stock:
            for line in self.order_line:
                if not line.commitment_date:
                    line.commitment_date = self.commitment_date
        return result