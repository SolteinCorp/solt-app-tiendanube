# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ConnectorSyncMixin(models.AbstractModel):
    """
    Mixin para añadir campos y métodos de sincronización a cualquier modelo
    que necesite sincronizarse con sistema externo.
    """
    _name = 'connector.sync.mixin'
    _description = 'Mixin de sincronización'

    is_being_synced = fields.Boolean('En sincronización', default=False, copy=False, prefetch=False)
    sync_source = fields.Selection([
        ('odoo', 'Desde Odoo'),
        ('store', 'Desde Tienda')
    ], string='Origen de sincronización', copy=False, prefetch=False)
    sync_timestamp = fields.Datetime('Tiempo de sincronización', copy=False, prefetch=False)

    def mark_as_syncing(self, source):
        """Marca el registro como en proceso de sincronización"""
        self.ensure_one()
        self.write({
            'is_being_synced': True,
            'sync_source': source,
            'sync_timestamp': fields.Datetime.now()
        })

    def can_sync_to_store(self):
        """Determina si este registro puede sincronizarse a la tienda"""
        self.ensure_one()
        return not (self.is_being_synced and self.sync_source == 'store')

    def can_sync_from_store(self):
        """Determina si este registro puede actualizarse desde la tienda"""
        self.ensure_one()
        return not (self.is_being_synced and self.sync_source == 'odoo')

    @api.model
    def clear_sync_flags(self):
        """
        Limpia los flags de sincronización para registros que han estado en
        estado de sincronización por más del tiempo umbral.
        """
        time_threshold = fields.Datetime.now() - timedelta(minutes=3)
        records_to_clear = self.search([
            ('is_being_synced', '=', True),
            ('sync_timestamp', '<', time_threshold)
        ])

        if records_to_clear:
            _logger.info(
                f"Limpiando flags de sincronización para {len(records_to_clear)} registros del modelo {self._name}")
            records_to_clear.write({
                'is_being_synced': False,
                'sync_source': False
            })

        return True

    @api.model
    def clear_all_sync_flags(self):
        """Limpia los flags de sincronización en todos los modelos sincronizables"""
        for model_name in self.env['connector.sync.mixin']._inherit_children:
            try:
                self.env[model_name].clear_sync_flags()
            except Exception as e:
                _logger.error(f"Error al limpiar flags de sincronización para el modelo {model_name}: {e}")

        return True
