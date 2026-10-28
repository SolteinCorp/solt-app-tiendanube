import logging
import os
import re

from odoo.api import SUPERUSER_ID, Environment
from odoo.modules.module import get_module_path

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Herramienta general para forzar fixes puntuales en registros protegidos por
# noupdate="1" a nivel de archivo (base_automation_data.xml,
# endpoints_tiendanube_data.xml, config_meta_field_data.xml, etc.).
#
# Por que hace falta: ese noupdate se chequea a nivel de ARCHIVO antes de que
# el flag propio de cada registro en ir.model.data importe (ver
# odoo/tools/convert.py, xml_import._tag_record) — asi que un `-u` normal
# nunca vuelve a aplicar los valores del XML en estos registros una vez que
# ya existen en la base, sin importar lo que digan sus flags individuales.
# Esto es intencional: protege ajustes que un cliente (o su tecnico) haya
# hecho a mano en cualquier campo de estos registros — por eso NO se le quita
# noupdate="1" a los archivos. Cuando de verdad se necesita que un fix nuestro
# llegue a bases ya instaladas, se escribe por ORM aqui, sin pasar por la
# carga de XML — mismo mecanismo, pero explicito y campo por campo, en vez de
# resetear el registro entero.
#
# Para agregar un fix nuevo: agrega una entrada a FORCE_SYNC_FIELDS con
# (archivo_en_data/, modelo, xmlid, [lista de campos a forzar]). Solo se
# tocan esos campos puntuales — cualquier otro campo que el cliente haya
# ajustado en ese mismo registro queda intacto.
# ---------------------------------------------------------------------------

FORCE_SYNC_FIELDS = [
    # (archivo en data/, modelo, xmlid, [campos a forzar])
    ('base_automation_data.xml', 'ir.actions.server', 'tn_ir_actions_server_ba_product_template_update', ['code']),
    ('base_automation_data.xml', 'ir.actions.server', 'tn_ir_actions_server_ba_product_product_update', ['code']),
    ('base_automation_data.xml', 'ir.actions.server', 'tn_ir_actions_server_ba_inventory_stock_update', ['code']),
]


def _extract_field_cdata(xml_content, model, xmlid, field_name):
    """Devuelve el contenido de <field name="{field_name}"><![CDATA[...]]></field>
    dentro de <record id="{xmlid}" ... model="{model}"> en el XML fuente."""
    pattern = (
        r'<record id="%s"[^>]*model="%s">'
        r'.*?<field name="%s">\s*<!\[CDATA\[(.*?)\]\]>\s*</field>'
    ) % (re.escape(xmlid), re.escape(model), re.escape(field_name))
    match = re.search(pattern, xml_content, re.DOTALL)
    return match.group(1) if match else None


def migrate(cr, version):
    """Fuerza campos puntuales de registros protegidos por noupdate="1" a
    tomar el valor actual del XML fuente, sin pasar por la carga normal de
    datos (que los ignoraria por el noupdate de archivo)."""
    if not version:
        return

    env = Environment(cr, SUPERUSER_ID, {})
    xml_cache = {}
    module_path = get_module_path('solt_tiendanube')

    for data_file, model, xmlid, field_names in FORCE_SYNC_FIELDS:
        if data_file not in xml_cache:
            xml_path = os.path.join(module_path, 'data', data_file) if module_path else None
            if not xml_path or not os.path.isfile(xml_path):
                _logger.error("No se encontro %s, se omiten sus fixes forzados.", data_file)
                xml_cache[data_file] = None
            else:
                with open(xml_path, encoding='utf-8') as f:
                    xml_cache[data_file] = f.read()

        xml_content = xml_cache[data_file]
        if xml_content is None:
            continue

        record = env.ref('solt_tiendanube.%s' % xmlid, raise_if_not_found=False)
        if not record:
            _logger.warning("No se encontro 'solt_tiendanube.%s' en esta base, se omite.", xmlid)
            continue

        values = {}
        for field_name in field_names:
            value = _extract_field_cdata(xml_content, model, xmlid, field_name)
            if value is None:
                _logger.warning(
                    "No se encontro el campo '%s' de '%s' en %s, se omite ese campo.",
                    field_name, xmlid, data_file,
                )
                continue
            values[field_name] = value

        if values:
            record.sudo().write(values)
            _logger.info("solt_tiendanube: forzados los campos %s en '%s'.", list(values.keys()), xmlid)
