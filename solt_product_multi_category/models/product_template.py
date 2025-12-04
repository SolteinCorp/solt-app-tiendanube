# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    categ_ids = fields.Many2many(
        comodel_name="product.category",
        relation="product_categ_rel",
        column1="product_tmpl_id",
        column2="categ_id",
        string="Categories",
        help="Additional categories for product classification. Categories created by store connectors."
    )