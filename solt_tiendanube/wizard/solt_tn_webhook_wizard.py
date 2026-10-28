# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models

_logger = logging.getLogger(__name__)


class SoltTnWebhookWizard(models.TransientModel):
    _name = 'solt.tn.webhook.wizard'
    _description = 'Tiendanube webhooks selection'

    line_ids = fields.One2many('solt.tn.webhook.wizard.line', 'wizard_id', string='Webhooks')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        connector = self.env.ref('solt_tiendanube.tn_connector_api')
        company = self.env.company
        has_webhooks, webhooks = connector._has_webhook_tn(company)
        if not has_webhooks:
            connector.action_create_tn_webhooks()
            _has, webhooks = connector._has_webhook_tn(company)
        res['line_ids'] = [
            Command.create({
                'webhook_id': webhook.id,
                'selected': webhook._tn_is_wanted(),
                'locked': not webhook.automation_id.tn_webhook_optional,
            })
            for webhook in webhooks.sorted(lambda w: (w.event or '', w.id))
        ]
        return res

    def action_confirm(self):
        """Publish the checked webhooks and remove from Tiendanube the unchecked ones
        that are already published. Automations are not activated here: that is a
        later onboarding step, after the initial sync."""
        self.ensure_one()
        company = self.env.company
        errors = []
        for line in self.line_ids:
            webhook = line.webhook_id.with_company(company)
            automation = webhook.automation_id
            try:
                if line.selected:
                    webhook.tn_publish_choice = 'yes'
                    if webhook.x_state_sync != 'yes':
                        webhook.with_context(wh_action='public').toggle_active()
                else:
                    webhook.tn_publish_choice = 'no'
                    if webhook.x_state_sync == 'yes':
                        webhook.with_context(wh_action='delete').toggle_active()
                    if automation.active:
                        automation.toggle_active()
            except Exception as error:
                _logger.warning("Webhook %s could not be processed: %s", webhook.event, error)
                errors.append("%s: %s" % (webhook.event, error))
        self.env.ref('solt_tiendanube.tn_connector_api')._onboarding_sync()
        if errors:
            return self.env['onboarding.onboarding.step'].solt_notification(
                _("Webhooks"), _("Some webhooks failed:\n%s", "\n".join(errors)), notif_type='warning')
        return {'type': 'ir.actions.act_window_close'}


class SoltTnWebhookWizardLine(models.TransientModel):
    _name = 'solt.tn.webhook.wizard.line'
    _description = 'Tiendanube webhooks selection line'

    wizard_id = fields.Many2one('solt.tn.webhook.wizard', required=True, ondelete='cascade')
    webhook_id = fields.Many2one('solt.register.webhook', required=True, ondelete='cascade')
    event = fields.Char(related='webhook_id.event')
    name = fields.Char(related='webhook_id.name')
    state_sync = fields.Char(string='Status in Tiendanube', compute='_compute_state_sync')
    selected = fields.Boolean('Publish')
    locked = fields.Boolean('Required', help="Required webhooks cannot be unchecked.")

    @api.depends('webhook_id')
    def _compute_state_sync(self):
        # x_state_sync is a dynamic (meta) field: it does not exist when the registry is set up.
        labels = {'yes': _("Published"), 'error': _("Error")}
        for line in self:
            state = line.webhook_id['x_state_sync'] if 'x_state_sync' in line.webhook_id._fields else False
            line.state_sync = labels.get(state, _("Not published"))
