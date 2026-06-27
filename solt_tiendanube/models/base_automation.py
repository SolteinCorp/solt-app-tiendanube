from odoo import models, fields


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