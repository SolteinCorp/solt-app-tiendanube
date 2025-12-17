# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
import json
import logging

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SoltApiCallLog(models.Model):
    _name = 'solt.api.call.log'
    _description = 'API Call Log'
    _order = 'create_date desc'

    connector_id = fields.Many2one('solt.api.connector', string='Conector API', required=True, ondelete='cascade')
    endpoint_id = fields.Many2one('solt.api.endpoint', string='Endpoint', ondelete='set null')

    request_url = fields.Char('URL', readonly=True)
    request_method = fields.Char('Método', readonly=True)
    request_headers = fields.Text('Headers', readonly=True)
    request_params = fields.Text('Parámetros', readonly=True)
    request_body = fields.Text('Cuerpo de la solicitud', readonly=True)

    response_code = fields.Integer('Código de respuesta', readonly=True)
    response_body = fields.Text('Cuerpo de la respuesta', readonly=True)

    duration = fields.Float('Duración (s)', digits=(10, 3), readonly=True)
    success = fields.Boolean('Éxito', default=False, readonly=True)

    name = fields.Char('Nombre', compute='_compute_name', store=True, readonly=True)

    @api.depends('create_date', 'endpoint_id', 'request_method')
    def _compute_name(self):
        for record in self:
            if record.create_date:
                date_str = fields.Datetime.to_string(record.create_date)
                endpoint_name = record.endpoint_id.name if record.endpoint_id else 'Desconocido'
                record.name = f"{date_str} - {record.request_method or 'GET'} {endpoint_name}"
            else:
                record.name = 'Nueva llamada'
