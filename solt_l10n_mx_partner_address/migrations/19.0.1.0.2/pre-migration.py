from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['ir.model.data'].search([['name', '=', 'mx'], ['module', '=', 'base']]).write({'noupdate': False})
