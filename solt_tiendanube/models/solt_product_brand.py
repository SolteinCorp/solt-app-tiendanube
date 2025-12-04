# -*- coding: utf-8 -*-

import logging
from odoo import models

_logger = logging.getLogger(__name__)


class SoltProductBrand(models.Model):
    _name = 'solt.product.brand'
    _inherit = ['solt.product.brand', 'solt.integration.model.mixin']