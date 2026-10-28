# -*- coding: utf-8 -*-
from odoo import _, api, models


class OnboardingOnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def _tn_connector(self):
        return self.env.ref('solt_tiendanube.tn_connector_api')

    @api.model
    def action_open_step_meta_fields(self):
        """Create (or retry creating) the dynamic sync fields and views."""
        connector = self._tn_connector()
        connector.action_create_all_meta_fields()
        connector._onboarding_sync()
        return self.solt_notification(_("Sync fields"), _("The synchronization fields are ready."))

    @api.model
    def action_open_step_connect_store(self):
        """Open the Tiendanube partners portal to start the app installation."""
        return self._tn_connector().action_open_install_url()

    @api.model
    def action_open_step_webhooks(self):
        wizard = self.env['solt.tn.webhook.wizard'].create({})
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tiendanube webhooks"),
            'res_model': 'solt.tn.webhook.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'dialog_size': 'large'},
        }

    @api.model
    def action_open_step_warehouses(self):
        wizard = self.env['solt.tn.warehouse.wizard'].create({})
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tiendanube warehouses"),
            'res_model': 'solt.tn.warehouse.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'dialog_size': 'large'},
        }

    @api.model
    def action_open_step_initial_sync(self):
        """List of the connector's initial import/export actions, with their run buttons."""
        connector = self._tn_connector()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Initial sync"),
            'res_model': 'ir.actions.server',
            'view_mode': 'list',
            'views': [(self.env.ref('solt_api_connector.view_ir_actions_server_initial_sync_list').id, 'list')],
            'domain': [
                ('connector_id', '=', connector.id),
                '|', ('use_for_initial_import', '=', True), ('use_for_initial_export', '=', True),
            ],
            'target': 'current',
        }

    @api.model
    def action_open_step_activate_automations(self):
        wizard = self.env['solt.tn.automation.wizard'].create({})
        return {
            'type': 'ir.actions.act_window',
            'name': _("Tiendanube automations"),
            'res_model': 'solt.tn.automation.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'dialog_size': 'large'},
        }

    @api.model
    def action_open_step_review(self):
        connector = self._tn_connector()
        connector._onboarding_sync()
        pending = [
            step['title'] for step in connector.get_onboarding_data()['steps']
            if not step['done'] and not step['optional'] and step['xmlid'] != 'solt_tiendanube.onboarding_step_review'
        ]
        if pending:
            return self.solt_notification(
                _("Review"), _("Pending steps: %s", ", ".join(pending)), notif_type='warning')
        return self.solt_notification(_("Review"), _("Everything is configured."))
