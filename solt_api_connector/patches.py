# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
"""
Patches aplicados al momento de cargar el módulo solt_api_connector.

Extiende odoo.tools.safe_eval._SAFE_OPCODES para soportar opcodes nuevos
introducidos en versiones recientes de Python (3.12+) que no están incluidos
en la lista de opcodes permitidos del core de Odoo.

Por qué es necesario:
    Python 3.12+ genera el opcode JUMP_BACKWARD_NO_INTERRUPT en el código de
    limpieza del compilador para bloques ``except Exception as e:``.
    Este opcode es semánticamente equivalente a JUMP_BACKWARD (salto hacia atrás
    sin comprobación de señales de interrupción) y no representa ningún riesgo
    de seguridad. Sin este parche, cualquier código de automatización
    (ir.actions.server / base.automation) que contenga un bloque
    ``except Exception as e:`` falla con:

        ValueError: forbidden opcode(s) in "...": JUMP_BACKWARD_NO_INTERRUPT

Compatibilidad:
    La función ``odoo.tools.safe_eval.to_opcodes`` usa ``if x in opmap``, por
    lo que los nombres de opcode que no existen en la versión actual de Python
    se ignoran silenciosamente. Este parche es seguro en Python 3.8 – 3.13+.
"""

import logging
from opcode import opmap

_logger = logging.getLogger(__name__)

# Opcodes introducidos en Python 3.12+ que Odoo no incluye aún en _SAFE_OPCODES.
# Se agregan solo si existen en el opmap de la versión de Python en ejecución.
_MISSING_SAFE_OPCODES = [
    # Python 3.12+: salto hacia atrás sin comprobación de interrupciones.
    # Generado por el compilador en la limpieza de variables en bloques
    # ``except Exception as e:`` y en el inner-loop de comprensiones.
    # Equivalente seguro de JUMP_BACKWARD (ya permitido por Odoo).
    'JUMP_BACKWARD_NO_INTERRUPT',
]


def _patch_safe_eval():
    """Agrega los opcodes faltantes a odoo.tools.safe_eval._SAFE_OPCODES."""
    try:
        import odoo.tools.safe_eval as _safe_eval_module

        added = []
        for opcode_name in _MISSING_SAFE_OPCODES:
            opcode_num = opmap.get(opcode_name)
            if opcode_num is not None and opcode_num not in _safe_eval_module._SAFE_OPCODES:
                _safe_eval_module._SAFE_OPCODES.add(opcode_num)
                added.append(opcode_name)

        if added:
            _logger.info(
                'solt_api_connector: safe_eval extendido con opcodes Python 3.12+: %s',
                ', '.join(added),
            )
    except Exception as e:
        _logger.warning(
            'solt_api_connector: No se pudo extender safe_eval._SAFE_OPCODES: %s', e
        )


_patch_safe_eval()

