# -*- coding: utf-8 -*-
{
    'name': "Sales Orders: Multi Warehouse",
    'summary': "Split sales fulfillment by warehouse per line",
    'description': """Adds configuration fields so Tiendanube orders can be routed to specific warehouses.""",
    'author': 'Soltein SA de CV',
    'maintainers': ['soltein'],
    'support': 'soporte@soltein.mx',
    'website': 'https://www.soltein.mx',
    'version': '18.0.1.0.3',
    'license': 'LGPL-3',
    'category': 'Soltein SA de CV/Stock',
    'application': False,
    'installable': True,
    'auto_install': False,
    'depends': ['sale_stock'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/sale_order_view.xml'
    ],
}
