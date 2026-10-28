# -*- coding: utf-8 -*-
from odoo import api, models

ONBOARDING_REQUIRED = 'solt_api_connector.onboarding_onboarding_connector'
ONBOARDING_OPTIONAL = 'solt_api_connector.onboarding_onboarding_connector_optional'


class OnboardingOnboardingStep(models.Model):
    _inherit = 'onboarding.onboarding.step'

    @api.model
    def solt_validate_step(self, xmlid):
        """Mark a connector onboarding step as done for the current company.

        Creates the progress record of the panels first, so the state is
        persisted even when nobody has opened the banner yet.
        """
        for panel_xmlid in (ONBOARDING_REQUIRED, ONBOARDING_OPTIONAL):
            panel = self.env.ref(panel_xmlid, raise_if_not_found=False)
            if panel:
                panel.sudo()._search_or_create_progress()
        result = self.sudo().action_validate_step(xmlid)
        if result == "JUST_DONE":
            self.env['solt.api.connector']._onboarding_step_changed()
        return result

    @api.model
    def solt_invalidate_step(self, xmlid):
        """Set a connector onboarding step back to pending for the current company.

        Odoo's progress only moves forward, so steps whose condition can stop
        being true (e.g. automations switched off again) are reverted here."""
        step = self.env.ref(xmlid, raise_if_not_found=False)
        if step:
            progress = step.sudo().current_progress_step_id
            if progress and progress.step_state != 'not_done':
                progress.step_state = 'not_done'
                self.env['solt.api.connector']._onboarding_step_changed()
        return True

    @api.model
    def solt_notification(self, title, message, notif_type='success', reload=False):
        """Client action used by the steps to report their result. With ``reload`` the
        current view is reloaded afterwards (keeping its breadcrumb); otherwise only the
        dialog is closed."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': notif_type,
                'sticky': False,
                'next': ({'type': 'ir.actions.client', 'tag': 'soft_reload'} if reload
                         else {'type': 'ir.actions.act_window_close'}),
            },
        }


class SoltApiConnector(models.Model):
    _inherit = 'solt.api.connector'

    def _onboarding_sync(self):
        """Hook: validate the steps whose real condition is already met.

        Connector-specific modules override it and call
        ``solt_validate_step`` for each satisfied step. Must be idempotent
        and must not call external services.
        """
        return True

    def _onboarding_blocked_reason(self, xmlid):
        """Hook: return a message when the step cannot be started yet."""
        return False

    def _onboarding_step_changed(self):
        """Hook: a step of the current company was completed or reverted.
        Connector-specific modules use it to report the new progress."""
        return True

    def _onboarding_summary(self):
        """Read-only summary of the onboarding of the current company, meant to be reported
        to the installation server: the first required step still pending and the state of
        every step. It does not recompute anything: call ``_onboarding_sync`` first."""
        self.ensure_one()
        steps = []
        current_step = False
        completed = True
        for panel_xmlid, optional in ((ONBOARDING_REQUIRED, False), (ONBOARDING_OPTIONAL, True)):
            panel = self.env.ref(panel_xmlid, raise_if_not_found=False)
            if not panel:
                continue
            for step in panel.sudo().step_ids.sorted(lambda s: (s.sequence, s.id)):
                xmlid = step.get_external_id().get(step.id) or ''
                key = xmlid.split('.')[-1].replace('onboarding_step_', '')
                done = step.current_step_state != 'not_done'
                steps.append({
                    'key': key,
                    'title': step.with_context(lang='es_MX').title,
                    'state': 'done' if done else 'pending',
                    'optional': optional,
                })
                if not optional and not done:
                    completed = False
                    current_step = current_step or key
        return {'current_step': current_step, 'completed': completed and bool(steps), 'steps': steps}

    def _onboarding_step_can_change(self, xmlid):
        """Hook: True when a completed step can be run again (shows a "Change" link)."""
        return False

    def _onboarding_step_detail(self, xmlid):
        """Hook: short summary shown under a completed step (or False)."""
        return False

    def action_sync_onboarding(self):
        for connector in self:
            connector._onboarding_sync()
        return True

    def get_onboarding_data(self):
        """Data for the connector form banner (steps, state, panel closed)."""
        self.ensure_one()
        self._onboarding_sync()
        panels = [
            (self.env.ref(ONBOARDING_REQUIRED, raise_if_not_found=False), False),
            (self.env.ref(ONBOARDING_OPTIONAL, raise_if_not_found=False), True),
        ]
        steps = []
        required_done = True
        closed = False
        for panel, optional in panels:
            if not panel:
                continue
            panel = panel.sudo()
            progress = panel._search_or_create_progress()
            if not optional:
                closed = progress.is_onboarding_closed
            for step in panel.step_ids.sorted(lambda s: (s.sequence, s.id)):
                xmlid = step.get_external_id().get(step.id)
                done = step.current_step_state != 'not_done'
                if not optional and not done:
                    required_done = False
                steps.append({
                    'id': step.id,
                    'xmlid': xmlid,
                    'title': step.title,
                    'description': step.description,
                    'button_text': step.button_text,
                    'done_text': step.done_text,
                    'action': step.panel_step_open_action_name,
                    'done': done,
                    'optional': optional,
                    'blocked': self._onboarding_blocked_reason(xmlid) if not done else False,
                    'detail': self._onboarding_step_detail(xmlid) if done else False,
                    'can_change': self._onboarding_step_can_change(xmlid),
                })
        return {
            'steps': steps,
            'closed': bool(closed),
            'completed': required_done and bool(steps),
            'panelId': panels[0][0].id if panels[0][0] else False,
        }
