# -*- coding: utf-8 -*-
from odoo import _, fields, models

STEP_PREFIX = 'solt_tiendanube.onboarding_step_'
STEPS_CAN_CHANGE = {
    STEP_PREFIX + 'webhooks',
    STEP_PREFIX + 'warehouses',
    STEP_PREFIX + 'initial_sync',
    STEP_PREFIX + 'activate_automations',
}
STEPS_NEED_STORE = {
    STEP_PREFIX + 'webhooks',
    STEP_PREFIX + 'warehouses',
    STEP_PREFIX + 'initial_sync',
    STEP_PREFIX + 'activate_automations',
}


class SoltApiConnector(models.Model):
    _inherit = 'solt.api.connector'

    def _is_tn_connector(self):
        tn_connector = self.env.ref('solt_tiendanube.tn_connector_api', raise_if_not_found=False)
        return bool(tn_connector) and self == tn_connector

    def _onboarding_blocked_reason(self, xmlid):
        if self._is_tn_connector() and xmlid in STEPS_NEED_STORE:
            company = self.env.company
            if not (company.external_id and company.bearer_token):
                return _("Requires connecting the store")
            if xmlid == STEP_PREFIX + 'activate_automations' and not self._tn_initial_sync_done():
                return _("Complete the initial sync first")
        return super()._onboarding_blocked_reason(xmlid)

    def _onboarding_step_changed(self):
        """Report the new progress to the installation server without waiting for the monthly
        heartbeat: schedule the "sync solt" cron, which sends the callback."""
        res = super()._onboarding_step_changed()
        cron = self.env.ref('solt_tiendanube.ir_cron_sync_tn_solt', raise_if_not_found=False)
        if cron:
            cron.sudo()._trigger()
        return res

    def _onboarding_step_can_change(self, xmlid):
        if self._is_tn_connector():
            return xmlid in STEPS_CAN_CHANGE
        return super()._onboarding_step_can_change(xmlid)

    def _onboarding_step_detail(self, xmlid):
        if self._is_tn_connector() and xmlid == STEP_PREFIX + 'activate_automations':
            update_store = self.env.ref('solt_tiendanube.tn_automation_update_store', raise_if_not_found=False)
            automations = self.env['base.automation'].with_context(active_test=False).search([
                ('connector_id', '=', self.id), ('id', '!=', update_store.id if update_store else 0)])
            webhook_automations = automations.filtered(lambda a: a.trigger == 'on_webhook')
            others = automations - webhook_automations
            return _("Webhooks: %(wh)s of %(wh_total)s active. Other automations: %(ot)s of %(ot_total)s active.",
                     wh=len(webhook_automations.filtered('active')), wh_total=len(webhook_automations),
                     ot=len(others.filtered('active')), ot_total=len(others))
        return super()._onboarding_step_detail(xmlid)

    def _tn_initial_sync_done(self):
        """The initial sync (an import, an export or both) is marked as completed by the user,
        per company, with the "Mark as completed" button of the initial sync list."""
        self.ensure_one()
        return self.env.company.state_initial_load == 'completed'

    def _tn_automations_ready(self):
        """True when the initial sync is done and the automations of every wanted,
        published webhook are active (the state the "Activate automations" step leaves)."""
        self.ensure_one()
        company = self.env.company
        if not (company.external_id and company.bearer_token) or not self._tn_initial_sync_done():
            return False
        _has, webhooks = self._has_webhook_tn(company)
        wanted = webhooks.filtered(lambda wh: wh._tn_is_wanted())
        return bool(wanted) and all(wh.x_state_sync == 'yes' and wh.automation_id.active for wh in wanted)

    def _onboarding_sync(self):
        res = super()._onboarding_sync()
        if not self._is_tn_connector():
            return res
        self.ensure_one()
        company = self.env.company
        Step = self.env['onboarding.onboarding.step']
        met = {}

        met['meta_fields'] = bool(self.env['ir.model.fields'].sudo().search_count([
            ('model', '=', 'product.template'), ('name', '=', 'x_external_id')]))
        has_store = bool(company.external_id and company.bearer_token)
        met['connect_store'] = has_store

        webhooks_ok = False
        if has_store:
            _has, webhooks = self._has_webhook_tn(company)
            wanted = webhooks.filtered(lambda wh: wh._tn_is_wanted())
            webhooks_ok = bool(wanted) and all(wh.x_state_sync == 'yes' for wh in wanted)
        met['webhooks'] = webhooks_ok

        mappings = self.env['solt.warehouse.sync.mapping'].sudo().search([('company_id', '=', company.id)])
        met['warehouses'] = has_store and bool(mappings) and all(mappings.mapped('is_synchronized'))
        if met['warehouses']:
            # The Warehouses step already imports and links the locations: reflect it in the
            # initial import actions list.
            import_action = self.env.ref('solt_tiendanube.tn_ir_actions_server_init_load_warehouse',
                                         raise_if_not_found=False)
            if import_action and import_action.sudo().importing_state != 'done':
                import_action.sudo().write({
                    'importing_state': 'done',
                    'last_import_date': fields.Datetime.now(),
                    'import_result': _("Completed from the Warehouses step."),
                })
        met['initial_sync'] = has_store and self._tn_initial_sync_done()

        # "Activate automations" is only completed by its wizard; here it is just reverted
        # when its conditions stop being true (initial sync pending, automations switched off).
        activate_step = self.env.ref(STEP_PREFIX + 'activate_automations', raise_if_not_found=False)
        activate_done = bool(activate_step) and activate_step.sudo().current_step_state != 'not_done'
        if activate_done and not self._tn_automations_ready():
            Step.solt_invalidate_step(STEP_PREFIX + 'activate_automations')
            activate_done = False
        met['activate_automations'] = activate_done
        met['review'] = all(met.values())

        for name, is_met in met.items():
            if name == 'activate_automations':
                continue
            if is_met:
                Step.solt_validate_step(STEP_PREFIX + name)
            else:
                Step.solt_invalidate_step(STEP_PREFIX + name)
        return res
