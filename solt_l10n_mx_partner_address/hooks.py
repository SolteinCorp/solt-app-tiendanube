# coding: utf-8

from odoo import tools
import csv


def post_init_hook(env):
    mx_country = env["res.country"].search([("code", "=", "MX")])
    # Load cities
    res_city_vals_list = []
    with tools.file_open("solt_l10n_mx_partner_address/data/res.city.csv") as csv_file:
        for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['l10n_mx_code', 'name', 'state_xml_id']):
            state = env.ref('base.%s' % row['state_xml_id'], raise_if_not_found=False)
            res_city_vals_list.append({
                'l10n_mx_code': row['l10n_mx_code'],
                'name': row['name'],
                'state_id': state.id if state else False,
                'country_id': mx_country.id,
            })

    existing_codes = set(env['res.city'].search([('l10n_mx_code', 'in', [v['l10n_mx_code'] for v in res_city_vals_list])]).mapped('l10n_mx_code'))
    res_city_vals_list = [city for city in res_city_vals_list if city['l10n_mx_code'] not in existing_codes]
    if res_city_vals_list:
        cities = env['res.city'].create(res_city_vals_list)

        env.cr.execute('''
           INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
               SELECT
                    'res_city_mx_' || lower(res_country_state.code) || '_' || res_city.l10n_mx_code,
                    res_city.id,
                    'solt_l10n_mx_partner_address',
                    'res.city',
                    TRUE
               FROM res_city
               JOIN res_country_state ON res_country_state.id = res_city.state_id
               WHERE res_city.id IN %s
        ''', [tuple(cities.ids)])

    # ==== Load l10n_mx_edi.res.locality ====

    if not env['res.locality'].search_count([]):
        res_locality_vals_list = []
        with tools.file_open("solt_l10n_mx_partner_address/data/res.locality.csv") as csv_file:
            for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['code', 'name', 'state_xml_id']):
                state = env.ref('base.%s' % row['state_xml_id'], raise_if_not_found=False)
                res_locality_vals_list.append({
                    'code': row['code'],
                    'name': row['name'],
                    'state_id': state.id if state else False,
                    'country_id': mx_country.id,
                })

        localities = env['res.locality'].create(res_locality_vals_list)

        if localities:
            env.cr.execute('''
               INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
                   SELECT 
                        'res_locality_mx_' || lower(res_country_state.code) || '_' || res_locality.code,
                        res_locality.id,
                        'solt_l10n_mx_partner_address',
                        'res.locality',
                        TRUE
                   FROM res_locality
                   JOIN res_country_state ON res_country_state.id = res_locality.state_id
                   WHERE res_locality.id IN %s
            ''', [tuple(localities.ids)])
