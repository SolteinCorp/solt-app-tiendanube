# -*- coding: utf-8 -*-

import logging
from odoo import models, fields, api, Command

_logger = logging.getLogger(__name__)


class Warehouse(models.Model):
    _name = 'stock.warehouse'
    _inherit = ['stock.warehouse', 'solt.integration.model.mixin']

    def form_code_from_name_api(self, data_name):
        """
        Returns the warehouse code formed by WH concatenated with
        the first three letters.
        :param data_name:
        :return: code
        """
        name = self.convert_translated_field_to_odoo_format(data_name, split_code=False)
        code = ''.join(word[0] for word in name.split()).upper()
        return 'WH' + code[:3]

    def _get_country_from_api(self, data):
        """
        Obtiene o crea un país desde los datos de la API de Tiendanube.
        :param data: dict con 'code' y 'name' del país
        :return: ID del país o False
        """
        Country = self.env['res.country'].sudo()
        if not isinstance(data, dict):
            return False

        code = data.get('code', '')
        name = data.get('name', '')

        country_id = Country.search(['|', ('name', '=ilike', name), ('code', '=ilike', code)], limit=1)
        if not country_id and name and code:
            country_id = Country.with_context(tracking_disable=True).create({
                'name': name,
                'code': code
            })

        return country_id and country_id.id or False

    def _get_state_from_api(self, data, country_id):
        """
        Obtiene o crea un estado/provincia desde los datos de la API de Tiendanube.
        :param data: dict con 'code' y 'name' del estado
        :param country_id: ID del país
        :return: ID del estado o False
        """
        State = self.env['res.country.state'].sudo()
        if not isinstance(data, dict):
            return False

        code = data.get('code', '')
        name = data.get('name', '')

        if not country_id or not name:
            return False

        state_id = State.search([('country_id', '=', country_id), '|', ('name', '=ilike', name), ('code', '=ilike', code)], limit=1)
        if not state_id:
            state_id = State.with_context(tracking_disable=True).create({
                'name': name,
                'code': code,
                'country_id': country_id
            })

        return state_id.id

    def _get_city_from_api(self, data, country_id, state_id):
        """
        Obtiene o crea una ciudad desde los datos de la API de Tiendanube.
        :param data: dict con datos de la dirección
        :param country_id: ID del país
        :param state_id: ID del estado
        :return: recordset de la ciudad o False
        """
        City = self.env['res.city'].sudo()
        if not isinstance(data, dict):
            return False

        name = data.get('city', '')

        if not country_id or not name:
            return False

        city_id = City.search([
            ('country_id', '=', country_id), ('state_id', 'in', [state_id, False]), ('name', '=ilike', name)
        ], limit=1)
        if not city_id:
            city_id = City.with_context(tracking_disable=True).create({
                'name': name,
                'country_id': country_id,
                'state_id': state_id
            })

        return city_id

    def _get_locality_from_api(self, data, country_id, state_id):
        """
        Obtiene o crea una localidad desde los datos de la API de Tiendanube.
        :param data: dict con datos de la dirección
        :param country_id: ID del país
        :param state_id: ID del estado
        :return: recordset de la localidad o False
        """
        Locality = self.env['res.locality'].sudo()
        if not isinstance(data, dict):
            return False

        name = data.get('locality', '')

        if not name or not country_id or not state_id:
            return False

        locality_id = Locality.search([
            ('country_id', '=', country_id), ('state_id', '=', state_id), ('name', '=ilike', name)
        ], limit=1)
        if not locality_id:
            locality_id = Locality.with_context(tracking_disable=True).create({
                'name': name,
                'country_id': country_id,
                'state_id': state_id
            })
        return locality_id

    def _get_or_create_partner_from_api(self, address_data, wh_name):
        if not isinstance(address_data, dict):
            return False

        country_id = self._get_country_from_api(address_data.get('country', {}))
        country = self.env['res.country'].browse(country_id)
        state_id = self._get_state_from_api(address_data.get('province', {}), country_id)
        region = address_data.get('region', {}).get('name')
        region_id = self.env['solt.region'].search([('country_id', '=', country_id), ('name', '=', region)])

        if country.enforce_cities:
            city_id = self._get_city_from_api(address_data, country_id, state_id)
            city = city_id and city_id.name or ''
        else:
            city_id = False
            city = address_data.get('city', '')

        if country.enforce_localities:
            locality_id = self._get_locality_from_api(address_data, country_id, state_id)
            l10n_mx_locality = ''
        else:
            locality_id = False
            l10n_mx_locality = address_data.get('locality', '')

        name = self.convert_translated_field_to_odoo_format(wh_name, split_code=False)
        company_id = self.env.company
        current_time = fields.Datetime.now()
        partner_values = {
            'name': name,
            'street_name': address_data.get('street', ''),
            'street2': address_data.get('between_streets', ''),
            'zip': address_data.get('zipcode', ''),
            'city_id': city_id and city_id.id or False,
            'city': city,
            'state_id': state_id,
            'country_id': country_id,
            'l10n_mx_locality_id': locality_id and locality_id.id or False,
            'l10n_mx_locality': l10n_mx_locality,
            'street_number': address_data.get('floor', ''),
            'street_number2': address_data.get('number', ''),
            'company_id': company_id.id,
            "x_state_sync": "yes",
            "x_date_last_sync": current_time,
            "x_store_external_id": company_id.external_id,
            "company_type": "company",
            "x_exclud_from_sync": True,
            "ref": address_data.get('reference', ''),
            'region_id': region_id and region_id.id or False,
        }

        return partner_values

        # partner = self.env['res.partner'].sudo().search([('name', '=', name), ('company_id', 'in', [False, company_id.id])], limit=1)
        # if partner:
        #     return partner.id
        # partner = self.env['res.partner'].sudo().create(partner_values)
        # return partner.id

    def prepare_address_to_api(self, value):
        if not isinstance(value, int):
            return {}
        partner = self.env['res.partner'].sudo().browse(value)
        country_val = {
            "name": partner.country_id.name or "",
            "code": partner.country_code
        }
        state_val = {
            "name": partner.state_id.name or "",
            "code": partner.state_id.code
        }
        region_val = {
            "name": partner.region_id and partner.region_id.name or "",
            "code": partner.region_id and partner.region_id.code or ""
        }
        if partner.country_id.enforce_cities and partner.city_id:
            city = partner.city_id and partner.city_id.name
        else:
            city = partner.city
        if partner.country_id.enforce_localities:
            locality = partner.self.l10n_mx_locality_id and partner.l10n_mx_locality_id.name
        else:
            locality = partner.l10n_mx_locality
        values = {
            "city": city or "",
            "country": country_val,
            "province": state_val,
            "locality": locality or "",
            "zipcode": partner.zip or "",
            "floor": partner.street_number,
            "number": partner.street_number2,
            "street": partner.street_name or "",
            "between_streets": partner.street2 or "",
            "reference": partner.ref or "",
            "region": region_val
        }
        return values

    def _get_default_inventory_level_api(self, type_product='consu'):
        if 'x_external_id' in self:
            warehouse_id = self.env['stock.warehouse'].with_company(self.env.company).search([
                ('x_external_id', 'not in', [False, ""]), ('company_id', '=', self.env.company.id)
            ], order="sequence, id ", limit=1)

            if warehouse_id:
                if type_product == 'consu':
                    inventory_level = [{
                        "location_id": warehouse_id.x_external_id,
                        "stock": 0
                    }]
                else:
                    inventory_level = [{
                        "location_id": warehouse_id.x_external_id,
                        "stock": ""
                    }]
                return inventory_level
        return []
