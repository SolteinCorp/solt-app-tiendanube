# -*- coding: utf-8 -*-
{
    'name': "Product Multi Categories",
    'summary': "Allow auxiliary categories for storefront connectors",
    'description': """Adds extra classification fields used during Tiendanube synchronization.""",
    'author': 'Soltein SA de CV',
    'maintainers': ['soltein'],
    'support': 'soporte@soltein.mx',
    'website': 'https://www.soltein.mx',
    'version': '18.0.1.0.1',
    'license': 'LGPL-3',
    'category': 'Soltein SA de CV/Product',
    'application': False,
    'installable': True,
    'auto_install': False,
    "depends": [
        "base",
        "product"
    ],
    "data": [
        "views/product_template_view.xml"
    ],
}
