# -*- coding: utf-8 -*-

from odoo import fields, models


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    api_meta_field_id = fields.Many2one(
        'solt.api.meta.fields',
        string='Configurar campos dinamicos',
        ondelete='cascade',
        help="Meta field configuration that created this dynamic field.",
    )
