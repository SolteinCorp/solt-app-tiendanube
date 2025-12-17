import csv

from odoo import api, SUPERUSER_ID, Command
from odoo.tools import file_open


def migrate(cr, version):
    """Post-migration: load city districts from CSV file."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    district_obj = env['res.city.district']
    imd_obj = env['ir.model.data']
    district_vals_list = []
    with file_open("solt_l10n_mx_partner_address/data/res.city.district.csv") as csv_file:
        for row in csv.DictReader(csv_file):
            city_id = env.ref(row['city_id'], raise_if_not_found=False).id
            if imd_obj._xmlid_to_res_id(f"solt_l10n_mx_partner_address.{row['id']}_{row['zipcode']}_{city_id}"):
                continue
            district_vals_list.append({
                'name': row['name'],
                'zip_code': row['zipcode'],
                'city_id': city_id,
            })

    districties = district_obj.create(district_vals_list)
    if districties:
        env.cr.execute('''
INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
   SELECT
        'colony_' || lower(replace(res_city_district.name, ' ', '_')) || '_' || res_city_district.zip_code || '_' || res_city_district.id,
         res_city_district.id,
        'solt_l10n_mx_partner_address',
        'res.city.district',
        TRUE
   FROM res_city_district
   JOIN res_city ON res_city.id = res_city_district.city_id
   WHERE res_city_district.id IN %s
                        ''', [tuple(districties.ids)])
