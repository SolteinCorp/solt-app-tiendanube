import logging
import os
import re

from odoo.api import SUPERUSER_ID, Environment
from odoo.modules.module import get_module_path

_logger = logging.getLogger(__name__)

# Record protected by noupdate="1": its code must take the new value of the XML (the import of
# the Tiendanube locations no longer creates a second mapping row for a location that has one).
FORCE_SYNC_FIELDS = [
    # (file in data/, model, xmlid, [fields])
    ('base_automation_data.xml', 'ir.actions.server', 'tn_ir_actions_server_init_load_warehouse', ['code']),
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
    for data_file, model, xmlid, field_names in FORCE_SYNC_FIELDS:
        xml_path = os.path.join(module_path, 'data', data_file) if module_path else None
        record = env.ref('solt_tiendanube.%s' % xmlid, raise_if_not_found=False)
        if not (xml_path and os.path.isfile(xml_path)) or not record:
            _logger.warning("%s skipped: file or record not found.", xmlid)
            continue
        with open(xml_path, encoding='utf-8') as xml_file:
            xml_content = xml_file.read()
        values = {}
        for field_name in field_names:
            value = _extract_field_cdata(xml_content, model, xmlid, field_name)
            if value is not None:
                values[field_name] = value
        if values:
            record.sudo().write(values)
            _logger.info("solt_tiendanube: forced %s on '%s'.", list(values), xmlid)


def migrate(cr, version):
    """Warehouse mappings upgrade (idempotent):
    - force the new import code of the locations (no duplicated rows),
    - remove the duplicated rows that older imports already created."""
    if not version:
        return
    env = Environment(cr, SUPERUSER_ID, {})
    _force_sync_fields(env)
    Mapping = env['solt.warehouse.sync.mapping']
    removed = sum(Mapping._cleanup_duplicate_pending(company) for company in env['res.company'].search([]))
    _logger.info("solt_tiendanube: %s duplicated warehouse mapping rows removed.", removed)
