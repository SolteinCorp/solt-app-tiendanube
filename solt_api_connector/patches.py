# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)

import logging
from opcode import opmap

import odoo.tools.safe_eval as safe_eval

_logger = logging.getLogger(__name__)


def patch_safe_eval_opcodes():
    """Extiende safe_eval para Python 3.12+/3.13 sin tocar core de Odoo.

    Python recientes generan JUMP_BACKWARD_NO_INTERRUPT en bloques
    ``except Exception as e:``, y safe_eval puede rechazar ese bytecode.
    """
    opcode = opmap.get('JUMP_BACKWARD_NO_INTERRUPT')
    if opcode is None:
        return

    if opcode not in safe_eval._SAFE_OPCODES:
        safe_eval._SAFE_OPCODES.add(opcode)
        _logger.info(
            'solt_api_connector: agregado opcode seguro a safe_eval: %s',
            'JUMP_BACKWARD_NO_INTERRUPT',
        )


patch_safe_eval_opcodes()

