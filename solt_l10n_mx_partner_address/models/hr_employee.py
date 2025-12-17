# -*- coding: utf-8 -*-

from odoo import api, fields, models


class HrEmployeePrivate(models.Model):
    _inherit = "hr.employee"

    private_locality = fields.Char(string="Locality Name", store=True, readonly=False, compute='_compute_private_locality', groups="hr.group_hr_user")
    private_locality_id = fields.Many2one(comodel_name='res.locality', string="Locality", groups="hr.group_hr_user",
                                          help="Optional attribute used in the XML that serves to define the locality where the domicile is located.")
    private_colony = fields.Char(string="Colony Name", groups="hr.group_hr_user")
    private_colony_code = fields.Char(string="Colony Code", groups="hr.group_hr_user",
                                      help="Note: Only use this field if this partner is the company address or if it is a branch office.\n"
                                           "Colony code that will be used in the CFDI with the external trade as Emitter colony. It must be a code "
                                           "from the SAT catalog.")
    private_street_number = fields.Char('House', groups="hr.group_hr_user")
    private_street_number2 = fields.Char('Door', groups="hr.group_hr_user")
    private_city_id = fields.Many2one(comodel_name='res.city', string='City ID', groups="hr.group_hr_user")
    country_enforce_cities = fields.Boolean(related='private_country_id.enforce_cities', groups="hr.group_hr_user")

    @api.depends('private_locality_id')
    def _compute_private_locality(self):
        for partner in self:
            partner.private_locality = partner.private_locality_id.name
