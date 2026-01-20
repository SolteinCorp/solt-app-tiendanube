from odoo import fields, models


class IrCron(models.Model):
    _inherit = 'ir.cron'

    server_action_to_import_id = fields.Many2one(
        'ir.actions.server',
        string='Server action for import',
        help="Server action currently being imported via this cron"
    )
    server_action_to_export_id = fields.Many2one(
        'ir.actions.server',
        string='Server action for export',
        help="Server action used for export via this cron"
    )

