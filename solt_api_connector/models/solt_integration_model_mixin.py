# -*- coding: utf-8 -*-

import logging

from odoo import models, api, fields

_logger = logging.getLogger(__name__)


class SoltIntegrationModelMixin(models.AbstractModel):
    _name = 'solt.integration.model.mixin'
    _description = 'Modelo de integración Mixin'

    def convert_translated_field_to_odoo_format(self, value, split_code=True):
        if not isinstance(value, dict):
            return value
        languages = self.env.lang
        if not languages:
            languages = self.env['res.lang'].get_installed()

        if split_code:
            if isinstance(languages, str):
                language_codes = {languages.split('_')[0]}
            else:
                language_codes = {lang[0].split('_')[0] for lang in languages if lang}
        else:
            if isinstance(languages, str):
                language_codes = {languages}
            else:
                language_codes = {lang[0] for lang in languages if lang}

        translation = ""
        for code in language_codes:
            if code in value:
                translation = value[code]
                break

        return translation

    def convert_translated_field_to_api_format(self, value, split_code=True):
        translation = {}
        languages = self.env.lang
        if not languages:
            languages = self.env['res.lang'].get_installed()

        if split_code:
            if isinstance(languages, str):
                language_codes = {languages.split('_')[0]}
            else:
                language_codes = {lang[0].split('_')[0] for lang in languages if lang}
        else:
            if isinstance(languages, str):
                language_codes = {languages}
            else:
                language_codes = {lang[0] for lang in languages if lang}

        # if split_code:
        #     language_codes = {languages.split('_')[0]}
        for code in language_codes:
            translation[code] = value if value else ''
        return translation

    def _check_can_update_record(self, values):
        """
        Valida si con el dict values se producirá un cambio real en el registro:
        - Para campos simples: compara directamente old != new.
        - Para Many2one/reference: compara old.id vs new (int o id en dict).
        - Para One2many/M2M: compara conjuntos de IDs actuales vs nuevos (incluso tras comandos).
        - Omite campos que empiecen por 'x_' o que no existan en el modelo.
        :param values: dict con valores a validar
        :return: True o False
        """
        if not isinstance(values, dict):
            return False

        def _extract_rel_ids(field, val):
            """Dado un valor val para un campo relacional, extrae el set de IDs resultante."""
            ftype = field.type
            # Many2one / reference
            if ftype in ('many2one', 'reference'):
                if isinstance(val, (int, str)):
                    try:
                        return {int(val)}
                    except ValueError:
                        return set()
                if isinstance(val, (list, tuple)) and len(val) >= 2 and isinstance(val[1], (int, str)):
                    return {int(val[1])}
                return set()
            # One2many / Many2many
            if ftype in ('one2many', 'many2many'):
                new_ids = set()
                if isinstance(val, list):
                    for cmd in val:
                        if isinstance(cmd, (list, tuple)) and len(cmd) >= 1:
                            code = cmd[0]
                            if code == 6 and len(cmd) >= 3:  # (6, 0, [ids])
                                new_ids.update(cmd[2] or [])
                            elif code == 4 and len(cmd) >= 2:  # (4, id)
                                new_ids.add(cmd[1])
                            elif code == 5:  # (5,) clear all
                                new_ids.clear()
                        elif isinstance(cmd, int):
                            new_ids.add(cmd)
                        elif isinstance(cmd, dict) and 'id' in cmd:
                            new_ids.add(cmd['id'])
                return new_ids
            return set()

        for field_name, new_value in values.items():
            if field_name.startswith('x_') or field_name not in self._fields:
                continue

            field = self._fields[field_name]
            ftype = field.type

            if ftype in ('many2one', 'one2many', 'many2many', 'reference'):
                old_val = getattr(self, field_name)
                if ftype in ('one2many', 'many2many'):
                    old_ids = set(old_val.ids)
                    new_ids = _extract_rel_ids(field, new_value)
                    if old_ids != new_ids:
                        return True
                else:
                    # many2one or reference
                    old_id = old_val.id if old_val else False
                    new_ids = _extract_rel_ids(field, new_value)
                    new_id = next(iter(new_ids), False)
                    if old_id != new_id:
                        return True
            else:
                old = getattr(self, field_name)
                # Convert basic types for comparison
                if isinstance(old, bool):
                    new = bool(new_value)
                elif isinstance(old, (int, float)) and isinstance(new_value, str):
                    try:
                        new = type(old)(new_value)
                    except Exception:
                        new = new_value
                else:
                    new = new_value
                if old != new:
                    return True

        return False

    @api.model
    def _get_connector(self):
        return self.env.company.connector_id

    @api.model
    def _get_endpoint_by_code(self, code):
        connector_id = self._get_connector()
        endpoint = self.env['solt.api.endpoint'].search([('code', '=', code), ('connector_id', '=', connector_id.id)], limit=1)
        return endpoint

