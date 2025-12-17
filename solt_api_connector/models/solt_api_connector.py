# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
import json

import base64
import logging
import requests

from odoo import models, fields, _, api
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class SoltApiConnector(models.Model):
    _name = 'solt.api.connector'
    _description = 'API Connector'

    name = fields.Char('Nombre', required=True)
    base_url = fields.Char('URL Base', required=True, help="URL base de la API (ej: https://api.example.com)")
    active = fields.Boolean('Activo', default=True)
    auth_type = fields.Selection([
        ('none', 'Sin autenticación'),
        ('basic', 'Autenticación Básica'),
        ('bearer', 'Token Bearer'),
        ('api_key', 'API Key'),
    ], string='Tipo de Autenticación', default='none', required=True)
    username = fields.Char('Usuario', help="Para autenticación básica")
    password = fields.Char('Contraseña', help="Para autenticación básica")
    token = fields.Char('Token', help="Para autenticación tipo Bearer o API Key")
    api_key_name = fields.Char('Nombre de API Key', help="Nombre del parámetro para la API Key")
    api_key_in = fields.Selection([('header', 'Header'), ('query', 'Query Parameter')], string='Ubicación de API Key', default='header')
    timeout = fields.Integer('Timeout (segundos)', default=30)
    headers = fields.Json('Headers adicionales', help="Headers adicionales en formato JSON")
    endpoint_ids = fields.One2many('solt.api.endpoint', 'connector_id', string='Endpoints')
    automation_ids = fields.One2many('base.automation', 'connector_id', string='Reglas de Automatización', context={'active_test': False},
                                     help="Reglas de automatización asociadas a este conector")
    company_ids = fields.One2many('res.company', 'connector_id', string='Compañías', help="Compañías asociadas a este conector")
    # En el modelo SoltApiConnector
    call_log_count = fields.Integer(string='Número de llamadas', compute='_compute_call_log_count')
    # Campos dinamicos
    meta_field_ids = fields.One2many('solt.api.meta.fields', 'connector_id', string="Campo meta")
    ini_import_acion_server_ids = fields.One2many('ir.actions.server', 'connector_id',
                                                  domain=[('use_for_initial_import', '=', True)],
                                                  string='Acciones de importacion inicial')
    company_count = fields.Integer(compute="_compute_company_count", string="Total de empresas sincronizadas")
    company_sync_count = fields.Integer(compute="_compute_company_count", string="Total de empresas sincronizadas")
    # Campos para exportación inicial
    ini_export_action_server_ids = fields.One2many('ir.actions.server', 'connector_id',
                                                   string='Acciones de exportación inicial',
                                                   domain=[('use_for_initial_export', '=', True)],
                                                   help="Acciones de servidor configuradas para exportación inicial")

    @api.depends()
    def _compute_call_log_count(self):
        """Calcula el número de logs de llamadas para este conector"""
        for connector in self:
            connector.call_log_count = self.env['solt.api.call.log'].search_count([
                ('connector_id', '=', connector.id)
            ])

    @api.depends('company_ids')
    def _compute_company_count(self):
        for connector in self:
            connector.company_count = len(connector.company_ids)
            connector.company_sync_count = len(
                connector.company_ids.filtered(lambda c: c.external_id and c.bearer_token))

    def action_view_call_logs(self):
        """Abre la vista de logs de llamadas filtradas por este conector"""
        self.ensure_one()
        return {
            'name': _('Logs de Llamadas API'),
            'type': 'ir.actions.act_window',
            'res_model': 'solt.api.call.log',
            'view_mode': 'tree,form',
            'domain': [('connector_id', '=', self.id)],
            'context': {'default_connector_id': self.id},
            'target': 'current',
        }

    @api.model
    def execute_endpoint(self, endpoint_code, record=None, params=None, data=None):
        """Ejecuta un endpoint dado su código y un diccionario de argumentos"""
        endpoint = self.env['solt.api.endpoint'].search([('code', '=', endpoint_code)], limit=1)
        if not endpoint:
            raise ValidationError(_("No se encontró el endpoint con el código: %s") % endpoint_code)
        try:
            response = endpoint.execute_request(record, params, data)
        except Exception as e:
            _logger.error(f"Error procesando respuesta: {str(e)}")
            raise UserError(str(e))
        return response

    def _get_auth_headers(self):
        """Prepara los headers de autenticación según el tipo configurado"""
        headers = {}
        if self.auth_type == 'basic':
            if not self.username or not self.password:
                raise ValidationError(_("Se requiere usuario y contraseña para autenticación básica."))
            auth_str = f"{self.username}:{self.password}"
            headers['Authorization'] = f"Basic {base64.b64encode(auth_str.encode()).decode()}"
        elif self.auth_type == 'bearer':
            if not self.token:
                raise ValidationError(_("Se requiere token para autenticación Bearer."))
            headers['Authorization'] = f"Bearer {self.token}"
        elif self.auth_type == 'api_key' and self.api_key_in == 'header':
            if not self.token or not self.api_key_name:
                raise ValidationError(_("Se requiere nombre y valor de API Key."))
            headers[self.api_key_name] = self.token
        # Agregar headers adicionales si existen
        if self.headers:
            headers.update(json.loads(self.headers))
        return headers

    def _prepare_api_url(self, endpoint):
        """Prepara la URL completa incluyendo la URL base y el endpoint"""
        if endpoint.startswith('https://') or endpoint.startswith('http://'):
            return endpoint.rstrip('/')
        base = self.base_url.rstrip('/')
        endpoint_path = endpoint.lstrip('/')
        return f"{base}/{endpoint_path}"

    def test_connection(self):
        """Prueba la conexión básica a la API"""
        try:
            headers = self._get_auth_headers()
            response = requests.get(self.base_url, headers=headers, timeout=self.timeout)
            if 200 <= response.status_code < 300:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Conexión exitosa'),
                        'message': _('La conexión a la API fue establecida correctamente.'),
                        'sticky': False,
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error de conexión'),
                        'message': _('La API respondió con código: %s - %s') % (response.status_code, response.text),
                        'sticky': True,
                        'type': 'warning',
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error de conexión'),
                    'message': str(e),
                    'sticky': True,
                    'type': 'danger',
                }
            }

    def action_all_active(self):
        for connector in self.with_context(active_test=False):
            connector.automation_ids.filtered(lambda a: not a.active).toggle_active()
        return True

    def action_all_inactive(self):
        for connector in self.with_context(active_test=False):
            connector.automation_ids.filtered(lambda a: a.active).toggle_active()
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active(self):
        if any(connector.active for connector in self):
            raise UserError(_('No puedes eliminar el conector de API en estado activo.'))

    def toggle_active(self):
        res = super().toggle_active()
        # Propagate active state to children
        for connector in self.with_context(active_test=False):
            connector.automation_ids.active = connector.active
        return res

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ['form']:
            for field in self._fields.keys():
                if field not in models.MAGIC_COLUMNS + ['active']:
                    field_node = next(iter(arch.xpath(f'//field[@name="{field}"]')), None)
                    if field_node is not None:
                        field_node.attrib['readonly'] = "not active"
        return arch, view

    def action_create_all_meta_fields(self):
        self.ensure_one()
        if self.meta_field_ids:
            for meta_field_id in self.meta_field_ids:
                meta_field_id.action_create_meta_fields()

    def unlink(self):
        for connector in self:
            # delete ini_import_acion_server_ids
            ini_import_acion_server_ids = self.env['ir.actions.server'].with_context(active_test=False).search([
                ('connector_id', '=', connector.id),
                ('use_for_initial_import', '=', True)
            ])
            ini_import_acion_server_ids.unlink()
            # delete meta fields config
            meta_field_ids = self.env['solt.api.meta.fields'].with_context(active_test=False).search([
                ('connector_id', '=', connector.id)
            ])
            meta_field_ids.unlink()

            # delete automations config
            automation_ids = self.env['base.automation'].with_context(active_test=False).search([
                ('connector_id', '=', connector.id)
            ])
            automation_ids.unlink()

            # delete ini_export_action_server_ids
            ini_export_action_server_ids = self.env['ir.actions.server'].with_context(active_test=False).search([
                ('connector_id', '=', connector.id),
                ('use_for_initial_export', '=', True)
            ])
            ini_export_action_server_ids.unlink()
        return super(SoltApiConnector, self).unlink()

