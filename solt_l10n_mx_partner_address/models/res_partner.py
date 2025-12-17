# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # == Address ==
    l10n_mx_locality = fields.Char(string="Locality Name", store=True, readonly=False, compute='_compute_l10n_mx_locality')
    l10n_mx_locality_id = fields.Many2one(comodel_name='res.locality', string="Locality",
                                          help="Optional attribute used in the XML that serves to define the locality where the domicile is located.")
    l10n_mx_colony = fields.Char(string="Colony Name")
    l10n_mx_colony_code = fields.Char(string="Colony Code",
                                      help="Note: Only use this field if this partner is the company address or if it is a branch office.\n"
                                           "Colony code that will be used in the CFDI with the external trade as Emitter colony. It must be a code "
                                           "from the SAT catalog.")

    @api.depends('l10n_mx_locality_id')
    def _compute_l10n_mx_locality(self):
        for partner in self:
            partner.l10n_mx_locality = partner.l10n_mx_locality_id.name

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return super(ResPartner, self)._formatting_address_fields() + ['l10n_mx_colony', 'l10n_mx_locality', 'l10n_mx_colony_code']
