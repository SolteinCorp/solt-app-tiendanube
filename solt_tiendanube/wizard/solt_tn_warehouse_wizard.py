# -*- coding: utf-8 -*-
import logging

from odoo import Command, _, api, fields, models

_logger = logging.getLogger(__name__)


class SoltTnWarehouseWizard(models.TransientModel):
    _name = 'solt.tn.warehouse.wizard'
    _description = 'Tiendanube warehouses linking'

    line_ids = fields.One2many('solt.tn.warehouse.wizard.line', 'wizard_id', string='Locations')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company
        Mapping = self.env['solt.warehouse.sync.mapping'].sudo()
        if not Mapping.search_count([('company_id', '=', company.id)]):
            self._import_locations(company)
        pending = Mapping.search([('company_id', '=', company.id)]).filtered(lambda m: not m.is_synchronized)
        res['line_ids'] = [
            Command.create({'mapping_id': mapping.id, 'warehouse_id': mapping.warehouse_id.id, 'create_new': not mapping.warehouse_id})
            for mapping in pending
        ]
        return res

    @api.model
    def _import_locations(self, company):
        """Run the connector's 'import warehouses' action to fill the mappings."""
        action = self.env.ref('solt_tiendanube.tn_ir_actions_server_init_load_warehouse', raise_if_not_found=False)
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        if action and warehouse:
            action.sudo().with_context(active_model='stock.warehouse', active_id=warehouse.id, active_ids=warehouse.ids).run()

    def action_confirm(self):
        self.ensure_one()
        errors = []
        for line in self.line_ids:
            mapping = line.mapping_id
            try:
                if line.warehouse_id:
                    mapping.warehouse_id = line.warehouse_id
                    mapping.action_sync_warehouse()
                elif line.create_new:
                    mapping.action_create_warehouse()
            except Exception as error:
                _logger.warning("Location %s could not be processed: %s", mapping.tn_name, error)
                errors.append("%s: %s" % (mapping.tn_name, error))
        self.env.ref('solt_tiendanube.tn_connector_api')._onboarding_sync()
        if errors:
            return self.env['onboarding.onboarding.step'].solt_notification(
                _("Warehouses"), _("Some locations failed:\n%s", "\n".join(errors)), notif_type='warning')
        return {'type': 'ir.actions.act_window_close'}


class SoltTnWarehouseWizardLine(models.TransientModel):
    _name = 'solt.tn.warehouse.wizard.line'
    _description = 'Tiendanube warehouses linking line'

    wizard_id = fields.Many2one('solt.tn.warehouse.wizard', required=True, ondelete='cascade')
    mapping_id = fields.Many2one('solt.warehouse.sync.mapping', required=True, ondelete='cascade')
    tn_name = fields.Char(related='mapping_id.tn_name', string='Tiendanube location')
    warehouse_id = fields.Many2one('stock.warehouse', string='Link to warehouse')
    create_new = fields.Boolean('Create warehouse', help="Create a new warehouse for this location.")

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        # Linking an existing warehouse replaces creating a new one; clearing it goes back to creating.
        for line in self:
            line.create_new = not line.warehouse_id
