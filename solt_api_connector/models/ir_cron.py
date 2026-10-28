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
    import_company_id = fields.Many2one(
        'res.company', string='Company of the import',
        help="Company that scheduled the import: the cron runs as the system user, so it is applied explicitly.",
        prefetch='False'
    )
    export_company_id = fields.Many2one(
        'res.company', string='Company of the export',
        help="Company that scheduled the export: the cron runs as the system user, so it is applied explicitly.",
        prefetch='False')
