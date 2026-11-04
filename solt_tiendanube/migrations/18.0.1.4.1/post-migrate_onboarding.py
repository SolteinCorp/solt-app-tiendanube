import logging
import os
import re

from odoo.api import SUPERUSER_ID, Environment
from odoo.modules.module import get_module_path

_logger = logging.getLogger(__name__)

OPTIONAL_WEBHOOK_AUTOMATIONS = [
    'tn_wh_automation_product_category_created',
    'tn_wh_automation_product_category_updated',
    'tn_wh_automation_product_category_deleted',
    'tn_wh_automation_product_created',
    'tn_wh_automation_product_updated',
    'tn_wh_automation_product_deleted',
]
REQUIRED_WEBHOOK_AUTOMATIONS = [
    'tn_wh_automation_fulfillment_updated',
    'tn_automation_app_uninstall',
    'tn_wh_automation_order_created',
    'tn_wh_automation_order_updated',
    'tn_wh_automation_order_cancelled',
    'tn_wh_automation_order_fulfilled',
    'tn_wh_automation_order_paid',
    'tn_wh_automation_order_edited',
]

# Records protected by noupdate="1" whose fields must take the new XML value
# (store email now goes to res.company.tn_email instead of email).
FORCE_SYNC_FIELDS = [
    # (file in data/, model, xmlid, [fields])
    ('endpoints_tiendanube_data.xml', 'solt.api.endpoint', 'endpoint_store', ['response_mapping']),
    ('base_automation_data.xml', 'ir.actions.server', 'tn_ir_actions_server_update_store', ['code']),
]


def _extract_field_cdata(xml_content, model, xmlid, field_name):
    pattern = (
        r'<record id="%s"[^>]*model="%s">'
        r'.*?<field name="%s">\s*<!\[CDATA\[(.*?)\]\]>\s*</field>'
    ) % (re.escape(xmlid), re.escape(model), re.escape(field_name))
    match = re.search(pattern, xml_content, re.DOTALL)
    return match.group(1) if match else None


def _force_sync_fields(env):
    module_path = get_module_path('solt_tiendanube')
    xml_cache = {}
    for data_file, model, xmlid, field_names in FORCE_SYNC_FIELDS:
        if data_file not in xml_cache:
            xml_path = os.path.join(module_path, 'data', data_file) if module_path else None
            if xml_path and os.path.isfile(xml_path):
                with open(xml_path, encoding='utf-8') as xml_file:
                    xml_cache[data_file] = xml_file.read()
            else:
                _logger.error("%s not found, its forced fixes are skipped.", data_file)
                xml_cache[data_file] = None
        xml_content = xml_cache[data_file]
        record = env.ref('solt_tiendanube.%s' % xmlid, raise_if_not_found=False)
        if xml_content is None or not record:
            continue
        values = {}
        for field_name in field_names:
            value = _extract_field_cdata(xml_content, model, xmlid, field_name)
            if value is not None:
                values[field_name] = value
        if values:
            record.sudo().write(values)
            _logger.info("solt_tiendanube: forced %s on '%s'.", list(values), xmlid)


def migrate(cr, version):
    """Onboarding + tn_email upgrade for existing databases (idempotent):
    - flag the optional webhook automations (noupdate="1" on the XML file),
    - copy the store email to tn_email and force the matching logic,
    - sync the onboarding state of the Tiendanube connector."""
    if not version:
        return
    env = Environment(cr, SUPERUSER_ID, {})

    for xmlids, optional in ((OPTIONAL_WEBHOOK_AUTOMATIONS, True), (REQUIRED_WEBHOOK_AUTOMATIONS, False)):
        for xmlid in xmlids:
            automation = env.ref('solt_tiendanube.%s' % xmlid, raise_if_not_found=False)
            if automation:
                automation.write({'tn_webhook_optional': optional})

    cr.execute("""
        UPDATE res_company
           SET tn_email = email
         WHERE external_id IS NOT NULL AND tn_email IS NULL
    """)
    _force_sync_fields(env)

    connector = env.ref('solt_tiendanube.tn_connector_api', raise_if_not_found=False)
    if connector:
        for company in env['res.company'].search([('external_id', '!=', False)]):
            try:
                connector.with_company(company)._onboarding_sync()
            except Exception as error:
                _logger.warning("Onboarding sync failed for %s: %s", company.name, error)
