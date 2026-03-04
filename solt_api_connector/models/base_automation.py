# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
import json
import traceback

from odoo import api, fields, models


class BaseAutomation(models.Model):
    _inherit = 'base.automation'

    connector_id = fields.Many2one('solt.api.connector', string='Connector',
                                   help="API connector linked to this automation rule.")
    endpoint_id = fields.Many2one('solt.api.endpoint', string='Endpoint',
                                  help="API endpoint executed by this automation rule.")
    sync_direction = fields.Selection([
        ('to_store', 'To external store'),
        ('from_store', 'From external store'),
    ], string='Sync direction', default='to_store',
        help="Direction of data synchronization: push to or pull from external store.")
    is_api_sync = fields.Boolean(string='Is API Sync', compute='_compute_is_api_sync', store=True, prefetch=False,
                                 help="Indicates whether this automation is linked to an API connector.")
    sequence = fields.Integer(string="Sequence", default=10, help="Order in which automations are executed.")

    @api.depends('trigger', 'trigger_field_ids', 'trg_selection_field_id', 'trg_field_ref')
    def _compute_filter_domain(self):
        non_connector_records = self.env['base.automation']
        for record in self:
            if record.connector_id and record.trigger not in ['on_state_set', 'on_priority_set', 'on_user_set', 'on_archive', 'on_unarchive']:
                trigger_fields_count = len(record.trigger_field_ids)
                if trigger_fields_count in [0, 1] and not record.filter_domain:
                    record.filter_domain = False
            else:
                non_connector_records |= record
        if non_connector_records:
            return super(BaseAutomation, non_connector_records)._compute_filter_domain()

    @api.depends('connector_id')
    def _compute_is_api_sync(self):
        for record in self:
            record.is_api_sync = bool(record.connector_id)

    def toggle_active(self):
        result = super(BaseAutomation, self).toggle_active()
        for record in self:
            if record.connector_id and record.trigger == 'on_webhook':
                # Webhook calls with a connector are logged in solt.api.call.log,
                # so ir.logging is not needed.
                record.log_webhook_calls = False
        return result

    def _get_webhook_log_vals(self, payload):
        """Hook for sub-modules to inject extra values into the webhook log.

        Override this method in connector-specific modules to add fields such as
        company_id derived from the incoming payload.
        """
        return {}

    def _execute_webhook(self, payload):
        """Override to redirect webhook logs to solt.api.call.log when a connector is set."""
        if not self.connector_id:
            return super()._execute_webhook(payload)

        call_log_vals = {
            'connector_id': self.connector_id.id,
            'automation_id': self.id,
            'request_url': self.url,
            'request_method': 'POST',
            'request_body': json.dumps(payload, default=str),
            'direction': 'incoming',
            'success': True,
        }
        call_log_vals.update(self._get_webhook_log_vals(payload))
        try:
            result = super()._execute_webhook(payload)
            return result
        except Exception:
            call_log_vals['success'] = False
            call_log_vals['response_body'] = traceback.format_exc()
            raise
        finally:
            self.env['solt.api.call.log'].sudo().create(call_log_vals)

    def _get_trigger_fields(self, record):
        """Return the trigger fields that have been modified on ``record``.
        Optionally exclude computed fields when requested via context."""
        self_sudo = self.sudo()
        _fields = []
        modified_fields = []
        ignore_computed = self._context.get('ignore_computed_fields', False)
        if not self_sudo.trigger_field_ids:
            # Every field is an implicit trigger
            fields_list = list(record._fields.keys())
        else:
            fields_list = self_sudo.trigger_field_ids.mapped('name')

        if self._context.get('old_values', None) is None:
            return modified_fields
        # note: old_vals are in the record format
        old_vals = self._context['old_values'].get(record.id, {})

        def differ(name):
            """Check if the field value changed compared to old values."""
            return name in old_vals and record[name] != old_vals[name]

        for field in fields_list:
            if field in models.MAGIC_COLUMNS:
                continue

            # Skip computed fields when requested
            if ignore_computed and field in record._fields:
                field_obj = record._fields[field]
                if field_obj.compute and not field_obj.store:
                    continue

            if differ(field):
                modified_fields.append(field)

        return modified_fields
