import hashlib
import hmac

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.http import request

# Default is the same TiendaNube app secret already used for the OAuth token
# exchange (see solt_tiendanube/data/endpoints_tiendanube_data.xml, endpoint TOKEN).
# Override via the 'solt_tiendanube.client_secret' System Parameter to rotate it
# without a code change.
_DEFAULT_TN_CLIENT_SECRET = 'a356cdf67a71ca483d309a56315744be646e6d5816531afc'
TN_SIGNATURE_HEADER = 'X-Linkedstore-Hmac-Sha256'


class BaseAutomation(models.Model):
    _inherit = 'base.automation'

    event = fields.Char("Event", prefetch=False, help="Evento de Tiendanube manejado por esta automatización.")
    tn_webhook_optional = fields.Boolean(
        "Webhook opcional", default=False, prefetch=False,
        help="Si está activo, este webhook no se publica automáticamente al aprovisionar (queda como avanzado).")

    def _prepare_tn_webhooks(self, company):
        self.ensure_one()
        return {
            'name': self.name,
            'event': self.event,
            'automation_id': self.id,
            'company_id': company.id,
        }

    def _get_webhook_log_vals(self, payload):
        """Resolve company_id from the TiendaNube store_id present in the payload.

        TiendaNube sends: {'store_id': 6024254, 'id': ..., 'event': '...'}
        store_id matches res.company.external_id set during store installation.
        """
        vals = super()._get_webhook_log_vals(payload)
        store_id = payload.get('store_id')
        if store_id:
            company = self.env['res.company'].sudo().search(
                [('external_id', '=', str(store_id))], limit=1
            )
            if company:
                vals['company_id'] = company.id
        return vals

    def _verify_webhook_signature(self, payload):
        """Validate the 'X-Linkedstore-Hmac-Sha256' header TiendaNube sends on
        every webhook delivery: HMAC-SHA256 of the raw request body, keyed with
        the app's client secret."""
        self.ensure_one()
        tn_connector = self.env.ref('solt_tiendanube.tn_connector_api', raise_if_not_found=False)
        if not self.connector_id or self.connector_id != tn_connector:
            return super()._verify_webhook_signature(payload)

        # "Actualizar Tienda" is not called by Tiendanube: /tiendanube/sync/install
        # invokes it internally, already authenticated by the Ed25519 signature of
        # the central server, so it carries no Tiendanube HMAC header.
        if self == self.env.ref('solt_tiendanube.tn_automation_update_store', raise_if_not_found=False):
            return

        secret =self.env['ir.config_parameter'].sudo().get_param(
            'solt_tiendanube.client_secret', _DEFAULT_TN_CLIENT_SECRET
        )
        received = request.httprequest.headers.get(TN_SIGNATURE_HEADER, '')
        computed = hmac.new(secret.encode(), request.httprequest.get_data(), hashlib.sha256).hexdigest()
        if not received or not hmac.compare_digest(computed, received):
            raise UserError('Firma de webhook invalida.')
