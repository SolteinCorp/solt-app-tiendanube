# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
{
    'name': "API Connector",
    'description': """Conector de API Genérico (SOLT API Connector)
=============================================

Este módulo permite configurar conectores a APIs externas de forma genérica y parametrizable:
* Definir múltiples conexiones a APIs externas
* Configurar endpoints con diferentes métodos (GET, POST, PUT, DELETE)
* Mapear campos entre modelos de Odoo y endpoints API
* Transformar datos en ambas direcciones
* Integrar con el sistema de automatización de Odoo (base_automation)
* Configurar webhooks para recibir notificaciones de APIs externas
* Programar sincronizaciones automáticas
* Registrar historial de llamadas API""",
    'author': 'Soltein SA de CV',
    'category': 'Soltein SA de CV/Tools',
    'version': '17.0.1.0.1',
    'website': 'https://soltein.mx',
    'license': 'LGPL-3',
    'depends': ['base', 'base_automation', 'social_media'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/res_company.xml',
        'views/solt_api_call_log.xml',
        'views/solt_api_connector.xml',
        'views/solt_api_endpoint.xml',
        'views/base_automation.xml',
        'views/ir_actions_server.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'solt_api_connector/static/src/scss/**/*',
        ]
    },
    'installable': True,
    'application': True,
}