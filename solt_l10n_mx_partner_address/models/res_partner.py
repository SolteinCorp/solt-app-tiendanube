# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # == Address ==
    l10n_mx_locality = fields.Char(string="Locality Name", store=True, readonly=False, prefetch=False)
    l10n_mx_locality_id = fields.Many2one(comodel_name='res.locality', string="Locality", prefetch=False,
                                          help="Optional attribute used in the XML that serves to define the locality where the domicile is located.")
    l10n_mx_colony = fields.Char(string="Colony Name")
    l10n_mx_colony_code = fields.Char(string="Colony Code", prefetch=False,
                                      help="Note: Only use this field if this partner is the company address or if it is a branch office.\n"
                                           "Colony code that will be used in the CFDI with the external trade as Emitter colony. It must be a code "
                                           "from the SAT catalog.")
    country_enforce_districts = fields.Boolean(string="Enforce Districts", compute='_compute_enforce', readonly=True, prefetch=False)
    country_enforce_localities = fields.Boolean(string="Enforce Localities", compute='_compute_enforce', readonly=True, prefetch=False)
    country_enforce_cities = fields.Boolean(related=False, compute='_compute_enforce', readonly=True, prefetch=False)
    district_id = fields.Many2one('res.city.district', string="District", prefetch=False)

    @api.depends('country_id')
    @api.onchange('country_id')
    def _compute_enforce(self):
        country = self.env.company.country_id
        for partner in self:
            partner.country_enforce_districts = partner.country_id.enforce_districts or (not partner.country_id and country.enforce_districts)
            partner.country_enforce_localities = partner.country_id.enforce_localities or (not partner.country_id and country.enforce_localities)
            partner.country_enforce_cities = partner.country_id.enforce_cities or (not partner.country_id and country.enforce_cities)

    @api.model
    def default_get(self, default_fields):
        values = super().default_get(default_fields)
        values['country_id'] = self.env.company.country_id.id or self.env.ref('base.mx').id
        return values

    def _get_complete_name(self):
        if self._context.get("show_full_name", ''):
            return self.name
        return super()._get_complete_name()

    def write(self, vals):
        res = super().write(vals)
        if 'district_id' in vals:
            self.write({'l10n_mx_colony': self.district_id.name, 'l10n_mx_colony_code': self.district_id.code or ''})
        return res

    @api.model
    def _address_fields(self):
        return super()._address_fields() + ['district_id', 'l10n_mx_colony', 'l10n_mx_locality', 'l10n_mx_colony_code', 'street_name', 'street_number', 'street_number2']

    @api.onchange('district_id')
    def _onchange_district_id(self):
        if self.country_enforce_districts and self.district_id and self.zip != self.district_id.zip_code:
            self.update({'zip': self.district_id.zip_code, 'l10n_mx_colony': self.district_id.name, 'l10n_mx_colony_code': self.district_id.code or '', 'city_id': self.district_id.city_id.id,
                        'city': self.district_id.city_id.name, 'state_id': self.district_id.city_id.state_id.id, 'country_id': self.district_id.city_id.state_id.country_id.id})

    @api.onchange('zip')
    def _onchange_zip(self):
        country = self.country_id or self.env.company.country_id
        if self.zip and self.country_enforce_districts and (not self.district_id or self.zip != self.district_id.zip_code):
            districts = self.env['res.city.district'].search([
                ('zip_code', '=', self.zip),
                ('city_id.state_id.country_id', '=', country.id),
            ])
            if not districts.exists():
                return {
                    'warning': {
                        'title': _('Warning'),
                        'message': _('The zip code does not exists.'),
                    }
                }
            district_id = districts[0]
            self.update({'district_id': district_id.id, 'l10n_mx_colony': district_id.name, 'l10n_mx_colony_code': district_id.code or '', 'city_id': district_id.city_id.id,
                        'city': district_id.city_id.name, 'state_id': district_id.city_id.state_id.id, 'country_id': district_id.city_id.state_id.country_id.id})

    @api.onchange('state_id')
    def _onchange_state_id(self):
        self.update({'district_id': False, 'l10n_mx_colony': False, 'l10n_mx_colony_code': False, 'city_id': False,
                     'city': False, 'country_id': self.state_id.country_id.id})

    @api.onchange('city_id')
    def _onchange_city_id(self):
        self.update({'district_id': False, 'l10n_mx_colony': False, 'l10n_mx_colony_code': False, 'state_id': self.city_id.state_id.id,
                     'city': self.city_id.name, 'country_id': self.city_id.state_id.country_id.id})

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        country_district_label = self.env.company.country_id.district_label
        if country_district_label:
            for node in arch.iterfind(".//field[@name='l10_mx_colony']"):
                node.set("string", country_district_label)
                node.set("placeholder", f"{country_district_label}...")
            for node in arch.iterfind(".//field[@name='district_id']"):
                node.set("string", country_district_label)
                node.set("placeholder", f"{country_district_label}...")
        for node in arch.iterfind(".//field[@name='city_id']"):
            node.set("string", _('Municipality'))
            node.set("placeholder", f"{_('Municipality')}...")
        for node in arch.iterfind(".//field[@name='city']"):
            node.set("string", _('Municipality'))
            node.set("placeholder", f"{_('Municipality')}...")
        return arch, view
