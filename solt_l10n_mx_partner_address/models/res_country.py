# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCountry(models.Model):
    _inherit = 'res.country'

    l10n_mx_code = fields.Char('Code MX',
                               help="Code of country defined by the SAT in the catalog for the CFDI version 4.0 and new complements. "
                                    "It will be used in the CFDI to indicate the country reference.")
