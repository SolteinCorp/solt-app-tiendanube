# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models

_logger = logging.getLogger(__name__)


class SoltTnAutomationWizard(models.TransientModel):
    _name = 'solt.tn.automation.wizard'
    _description = 'Tiendanube automations activation'

    line_ids = fields.One2many('solt.tn.automation.wizard.line', 'wizard_id', string='Automations')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        connector = self.env.ref('solt_tiendanube.tn_connector_api')
        company = self.env.company
        update_store = self.env.ref('solt_tiendanube.tn_automation_update_store', raise_if_not_found=False)
        automations = self.env['base.automation'].with_context(active_test=False).search([
            ('connector_id', '=', connector.id), ('id', '!=', update_store.id if update_store else 0),
        ])
        _has, webhooks = connector._has_webhook_tn(company)
        webhook_by_automation = {webhook.automation_id.id: webhook for webhook in webhooks}
        lines = []
        for automation in automations.sorted(lambda a: (a.trigger != 'on_webhook', a.trigger, a.name or '')):
            webhook = webhook_by_automation.get(automation.id)
            if automation.trigger == 'on_webhook':
                published = bool(webhook) and webhook.x_state_sync == 'yes'
                selected = published and webhook._tn_is_wanted()
                locked = not published
            else:
                selected, locked = automation.active, False
            lines.append(Command.create({
                'automation_id': automation.id,
                'selected': selected,
                'locked': locked,
                'webhook_id': webhook.id if webhook else False,
            }))
        res['line_ids'] = lines
        return res

    def action_confirm(self):
        """Activate the checked automations and deactivate the unchecked ones.
        Automations of webhooks that are not published stay untouched."""
        self.ensure_one()
        activated = deactivated = 0
        for line in self.line_ids.filtered(lambda l: not l.locked):
            automation = line.automation_id
            if line.selected and not automation.active:
                automation.write({'active': True})
                activated += 1
            elif not line.selected and automation.active:
                automation.write({'active': False})
                deactivated += 1
        connector = self.env.ref('solt_tiendanube.tn_connector_api')
        if connector._tn_automations_ready():
            self.env['onboarding.onboarding.step'].solt_validate_step(
                'solt_tiendanube.onboarding_step_activate_automations')
        connector._onboarding_sync()
        return self.env['onboarding.onboarding.step'].solt_notification(
            _("Automations"),
            _("%(activated)s automations activated, %(deactivated)s deactivated.",
              activated=activated, deactivated=deactivated),
            reload=True)


class SoltTnAutomationWizardLine(models.TransientModel):
    _name = 'solt.tn.automation.wizard.line'
    _description = 'Tiendanube automations activation line'

    wizard_id = fields.Many2one('solt.tn.automation.wizard', required=True, ondelete='cascade')
    automation_id = fields.Many2one('base.automation', required=True, ondelete='cascade')
    name = fields.Char(related='automation_id.name')
    trigger = fields.Selection(related='automation_id.trigger')
    model_name = fields.Char(related='automation_id.model_id.name', string='Model')
    webhook_id = fields.Many2one('solt.register.webhook')
    is_active = fields.Boolean('Active now', related='automation_id.active')
    selected = fields.Boolean('Activate')
    locked = fields.Boolean('Webhook not published', help="The webhook of this automation is not published in Tiendanube yet.")
