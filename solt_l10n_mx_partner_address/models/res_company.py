# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # == Address ==
    l10n_mx_locality = fields.Char(string='Locality', compute='_compute_l10n_mx_locality', inverse='_inverse_l10n_mx_locality')
    l10n_mx_locality_id = fields.Many2one('res.locality', string='Locality',
    related='partner_id.l10n_mx_locality_id', readonly=False,
                                          compute_sudo=True,
                                          help='Municipality configured for this company')
    l10n_mx_colony_code = fields.Char(string='Colony Code', compute='_compute_l10n_mx_colony_code', inverse='_inverse_l10n_mx_colony_code', help='Colony Code configured for this company. It is used in the external trade complement to define the colony where the domicile is located.')
    l10n_mx_colony = fields.Char(string='Colony', compute='_compute_l10n_mx_colony', inverse='_inverse_l10n_mx_colony')
    # Technical field to hide country specific fields in company form view
    country_code = fields.Char(related='country_id.code', depends=['country_id'], compute_sudo=True)

    def _compute_l10n_mx_locality(self):
        for company in self:
            address_data = company.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = company.partner_id.sudo().browse(address_data['contact'])
                company.l10n_mx_locality = partner.l10n_mx_locality
            else:
                company.l10n_mx_locality = None

    def _inverse_l10n_mx_locality(self):
        for company in self:
            company.partner_id.l10n_mx_locality = company.l10n_mx_locality

    def _compute_l10n_mx_colony(self):
        for company in self:
            address_data = company.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = company.partner_id.sudo().browse(address_data['contact'])
                company.l10n_mx_colony = partner.l10n_mx_colony
            else:
                company.l10n_mx_colony = None

    def _inverse_l10n_mx_colony(self):
        for company in self:
            company.partner_id.l10n_mx_colony = company.l10n_mx_colony

    def _compute_l10n_mx_colony_code(self):
        for company in self:
            address_data = company.partner_id.sudo().address_get(adr_pref=['contact'])
            if address_data['contact']:
                partner = company.partner_id.browse(address_data['contact'])
                company.l10n_mx_colony_code = partner.l10n_mx_colony_code

    def _inverse_l10n_mx_colony_code(self):
        for company in self:
            company.partner_id.l10n_mx_colony_code = company.l10n_mx_colony_code

    # ----------------------------------------------------------
    # View customization
    # ----------------------------------------------------------
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        company_vat_label = self.env.company.country_id.vat_label
        if company_vat_label:
            for node in arch.iterfind(".//field[@name='vat']"):
                node.set("string", company_vat_label)
        return arch, view
