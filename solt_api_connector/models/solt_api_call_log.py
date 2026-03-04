# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class SoltApiCallLog(models.Model):
    _name = 'solt.api.call.log'
    _description = 'API Call Log'
    _order = 'create_date desc'

    connector_id = fields.Many2one('solt.api.connector', string='API Connector', required=True, ondelete='cascade',
                                   help="API connector that made this call.")
    endpoint_id = fields.Many2one('solt.api.endpoint', string='Endpoint', ondelete='set null',
                                  help="Endpoint that was called.")

    request_url = fields.Char('Request URL', readonly=True, help="Full URL of the request.")
    request_method = fields.Char('HTTP method', readonly=True, help="HTTP method used (GET, POST, etc.).")
    request_headers = fields.Text('Request headers', readonly=True, help="Headers sent with the request.")
    request_params = fields.Text('Request parameters', readonly=True, help="Query parameters sent with the request.")
    request_body = fields.Text('Request payload', readonly=True, help="Body/payload sent with the request.")

    response_code = fields.Integer('Response code', readonly=True, help="HTTP status code returned by the API.")
    response_body = fields.Text('Response payload', readonly=True, help="Response body returned by the API.")

    duration = fields.Float('Duration (s)', digits=(10, 3), readonly=True, help="Time taken for the API call in seconds.")
    success = fields.Boolean('Successful', default=False, readonly=True, help="Whether the API call was successful (2xx).")

    name = fields.Char('Name', compute='_compute_name', store=True, readonly=True,
                        help="Auto-generated name combining date, method and endpoint.")
    automation_id = fields.Many2one('base.automation', string='Automation', ondelete='set null', readonly=True,
                                    help="Related automation if this call was triggered by one.")
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 help="Related company if this call was triggered by one.")
    direction = fields.Selection(
        [('outgoing', 'Outgoing'), ('incoming', 'Incoming')],
        string='Direction',
        default='outgoing',
        readonly=True,
        help="Direction of the API call: 'Outgoing' if initiated by Odoo to an external API, 'Incoming' if received from an external source (e.g. webhook)."
    )

    @api.depends('create_date', 'endpoint_id', 'automation_id', 'request_method', 'direction')
    def _compute_name(self):
        for record in self:
            if record.create_date:
                date_str = fields.Datetime.to_string(record.create_date)
                if record.endpoint_id:
                    label = record.endpoint_id.name
                elif record.automation_id:
                    label = record.automation_id.name
                else:
                    label = _('Unknown endpoint')
                http_method = record.request_method or ('POST' if record.direction == 'incoming' else 'GET')
                record.name = f"{date_str} - {http_method} {label}"
            else:
                record.name = _('New API call')
