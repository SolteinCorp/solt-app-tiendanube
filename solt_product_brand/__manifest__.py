# -*- coding: utf-8 -*-
{
    'name': "Product Brand Management",
    'summary': "Assign and maintain custom brand dictionaries on products",
    'description': """Exposes brand records for Tiendanube sync and internal analytics.""",
    'author': 'Soltein SA de CV',
    'maintainers': ['soltein'],
    'support': 'soporte@soltein.mx',
    'website': 'https://www.soltein.mx',
    'version': '18.0.1.0.2',
    'license': 'LGPL-3',
    'category': 'Soltein SA de CV/Product',
    'application': False,
    'installable': True,
    'auto_install': False,

    # any module necessary for this one to work correctly
    'depends': ['stock'],

    # always loaded
    'data': [
        'security/ir_rule.xml',
        'security/ir.model.access.csv',
        'views/solt_product_brand_views.xml',
        'views/product_template_views.xml',

        'views/menus.xml'
    ],
}
