# -*- coding: utf-8 -*-
{
    'name': "Mexican Partner Address",
    'countries': ['mx'],
    'version': '1.0',
    'category': 'Hidden',
    'license': 'LGPL-3',
    'author': 'Soltein SA de CV',
    'website': 'https://www.soltein.mx',
    'depends': [
        'base_setup',
        'base_address_extended',
        'solt_base_entities',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_employee.xml',
        'views/res_company.xml',
        'views/res_partner.xml',
        'views/res_country.xml',
        'views/res_locality.xml',
        'data/res_country.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'post_init_hook': 'post_init_hook',
}
