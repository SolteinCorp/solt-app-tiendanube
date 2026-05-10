# -*- coding: utf-8 -*-
import time

from odoo import api, fields, models


class TiendaNubeSyncNonce(models.Model):
    _name = 'solt.tiendanube.sync.nonce'
    _description = 'TiendaNube sync request nonce (replay protection)'
    _rec_name = 'value'

    key_id = fields.Char(
        string="Key ID",
        required=True,
        index=True,
        help="Identifier of the signing key associated with this nonce.",
    )
    value = fields.Char(
        string="Nonce",
        required=True,
        index=True,
        help="Unique nonce value used to prevent replay attacks.",
    )
    expires_at = fields.Integer(
        string="Expires At",
        required=True,
        help="Unix epoch seconds at which this nonce expires and can be garbage-collected.",
    )

    _uniq_nonce = models.Constraint(
        "unique(key_id, value)",
        "Replayed nonce",
    )

    @api.model
    def gc_expired(self):
        """Garbage-collect nonces whose ``expires_at`` is in the past."""
        self.search([('expires_at', '<', int(time.time()))]).unlink()
