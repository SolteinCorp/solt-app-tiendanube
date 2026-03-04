# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ConnectorSyncMixin(models.AbstractModel):
    """
    Mixin to add fields and methods for synchronization to any model
    that needs to synchronize with an external system.
    """
    _name = 'connector.sync.mixin'
    _description = 'Connector Sync Mixin'

    is_being_synced = fields.Boolean('In synchronization', default=False, copy=False, prefetch=False,
                                     help="Flag indicating the record is currently being synchronized.")
    sync_source = fields.Selection([
        ('odoo', 'From Odoo'),
        ('store', 'From Store')
    ], string='Synchronization source', copy=False, prefetch=False,
        help="Origin of the current synchronization process.")
    sync_timestamp = fields.Datetime('Synchronization time', copy=False, prefetch=False,
                                     help="Timestamp when the current sync operation started.")
    x_external_id = fields.Char('External ID', readonly=True,
                                help="ID of the record in the external system.")
    x_store_external_id = fields.Char('Store external ID', readonly=True,
                                      help="External store identifier for this record.")
    x_state_sync = fields.Selection([
        ('yes', 'In sync'),
        ('no', 'Pending sync'),
        ('error', 'Error'),
    ], string='Sync status', default='no', readonly=True,
        help="Indicates whether the record is synchronized with the external system.")
    x_exclud_from_sync = fields.Boolean('Exclude from sync', default=False,
                                        help="When enabled, the record will not be exported to external systems.")
    x_date_last_sync = fields.Datetime('Last synchronization', readonly=True,
                                       help="Timestamp of the last successful synchronization.")

    def mark_as_syncing(self, source):
        """Marks the record as being synchronized"""
        self.ensure_one()
        self.write({
            'is_being_synced': True,
            'sync_source': source,
            'sync_timestamp': fields.Datetime.now()
        })

    def can_sync_to_store(self):
        """Determines if this record can be synchronized to the store"""
        self.ensure_one()
        return not (self.is_being_synced and self.sync_source == 'store')

    def can_sync_from_store(self):
        """Determines if this record can be updated from the store"""
        self.ensure_one()
        return not (self.is_being_synced and self.sync_source == 'odoo')

    @api.model
    def clear_sync_flags(self):
        """
        Clears the synchronization flags for records that have been in
        synchronization status for more than the threshold time.
        """
        time_threshold = fields.Datetime.now() - timedelta(minutes=3)
        records_to_clear = self.search([
            ('is_being_synced', '=', True),
            ('sync_timestamp', '<', time_threshold)
        ])

        if records_to_clear:
            _logger.info(
                f"Clearing synchronization flags for {len(records_to_clear)} records of the model {self._name}")
            records_to_clear.write({
                'is_being_synced': False,
                'sync_source': False
            })

        return True

    @api.model
    def clear_all_sync_flags(self):
        """Clears the synchronization flags in all syncable models"""
        for model_name in self.env['connector.sync.mixin']._inherit_children:
            try:
                self.env[model_name].clear_sync_flags()
            except Exception as e:
                _logger.error(f"Error clearing synchronization flags for the model {model_name}: {e}")

        return True
