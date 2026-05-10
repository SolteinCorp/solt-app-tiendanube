# -*- coding: utf-8 -*-
import json
import logging

import requests
from odoo import http
from odoo.exceptions import UserError
from odoo.http import request, route

from ..tn_security import (
    HEADER_KEY_ID,
    MASTER_PUBLIC_KEYS,
    TARGET_KEY_ID,
    TARGET_PUBLIC_KEY,
    SignatureError,
    consume_nonce,
    get_master_public_key,
    verify_signature,
)

_logger = logging.getLogger(__name__)


class TiendaNubeSyncController(http.Controller):

    @route(['/tiendanube/sync/install'], type='http', auth='public', methods=['POST'], csrf=False)
    def tiendanube_sync_install(self, **kwargs):
        """
        Receive a signed sync request from the Soltein master and execute the
        synchronization. The signature is verified against the master public
        keys hardcoded in tn_security.MASTER_PUBLIC_KEYS so the destination
        does not need any out-of-band configuration.

        On a multi-database destination, the master pre-establishes a session
        cookie bound to the target database (via a bootstrap GET to
        ``/web?db=<name>``) and reuses it on this POST so the dispatcher
        resolves the correct database before this controller runs.
        """
        if not MASTER_PUBLIC_KEYS:
            _logger.error("/tiendanube/sync/install rejected: MASTER_PUBLIC_KEYS is empty in module source.")
            return request.make_response('Master keys not provisioned in this module build', status=503)

        raw_body = request.httprequest.get_data(cache=True) or b''
        headers = request.httprequest.headers
        master_key_id = headers.get(HEADER_KEY_ID)
        master_pub = get_master_public_key(master_key_id)
        if not master_pub:
            _logger.warning("/tiendanube/sync/install rejected: unknown master KeyId %r", master_key_id)
            return request.make_response('Unknown key id', status=401)
        try:
            verify_signature(
                master_pub,
                request.httprequest.method,
                request.httprequest.path,
                headers,
                raw_body,
            )
            consume_nonce(request.env, master_key_id, headers.get('X-TN-Nonce'))
        except SignatureError as exc:
            _logger.warning("/tiendanube/sync/install rejected: %s", exc)
            return request.make_response('Invalid signature', status=401)

        try:
            try:
                sync_data = json.loads(raw_body.decode('utf-8') or '{}')
            except (ValueError, UnicodeDecodeError):
                return request.make_response('Malformed JSON', status=400)
            _logger.info(f"Synchronization data received: {sync_data}")
            if not self._validate_sync_data(sync_data):
                return request.make_response('Invalid data', status=400)
            result = self._execute_store_update_automation(sync_data)
            if not result.get('success'):
                _logger.error(f"Store update error: {result.get('error_message')}")
                return request.make_response('Store update error', status=500)
            _logger.info(f"Store updated successfully: {result}")
            request.env.ref('solt_tiendanube.ir_cron_sync_tn_solt').sudo()._trigger()

            return request.make_json_response({
                'ok': True,
                'target_public_key': TARGET_PUBLIC_KEY,
                'target_key_id': TARGET_KEY_ID,
            })

        except Exception as e:
            error_msg = f"Synchronization error: {str(e)}"
            _logger.error(error_msg)
            return request.make_response('Internal server error', status=500)

    def _validate_sync_data(self, sync_data):
        required_fields = ['store_info', 'sync_token', 'odoo_version', 'callback_url']
        return all(field in sync_data for field in required_fields)

    def _execute_store_update_automation(self, sync_data):
        sync_token = sync_data.get('sync_token')
        try:
            base_automation = request.env.ref('solt_tiendanube.tn_automation_update_store').sudo()
            if not base_automation:
                raise UserError("Automated rule 'UPDATE STORE' not found or inactive.")
            if not base_automation.url:
                raise UserError("The automated rule 'UPDATE STORE' does not have a configured URL.")
            _logger.info(f"Executing automated rule: {base_automation.name} at URL: {base_automation.url}")
            store_info = sync_data.get('store_info', {})
            payload = store_info.copy()
            payload['sync_token'] = sync_token
            payload['callback_url'] = sync_data.get('callback_url')
            result = self._call_webhook_url(base_automation, payload)

            return {
                'success': True,
                'company_id': result.get('company_id'),
                'company_name': result.get('company_name'),
                'company_email': result.get('company_email'),
                'sync_token': sync_token,
            }

        except Exception as e:
            _logger.error(f"Error executing automated rule: {str(e)}")
            return {
                'success': False,
                'error_message': str(e),
                'sync_token': sync_token,
            }

    def _call_webhook_url(self, base_automation, payload):
        try:
            webhook_url = base_automation.url
            if webhook_url.startswith('/'):
                base_url = request.httprequest.host_url.rstrip('/')
                webhook_url = f"{base_url}{webhook_url}"

            _logger.info(f"Llamando webhook URL: {webhook_url}")

            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Odoo-Tiendanube-Integration',
                'X-Forwarded-For': request.httprequest.remote_addr,
                'X-Real-IP': request.httprequest.remote_addr,
            }

            if hasattr(base_automation, 'connector_id') and base_automation.connector_id:
                if hasattr(base_automation.connector_id, 'get_auth_headers'):
                    auth_headers = base_automation.connector_id.get_auth_headers()
                    headers.update(auth_headers)

            # Self-HTTP-call: re-enter Odoo through WSGI for the automation
            # webhook. On a multi-database destination this re-entry needs a
            # session cookie that is bound to the current database; otherwise
            # the dispatcher cannot pick a database and replies 404. We
            # forward the inbound cookie when present, falling back to a
            # bootstrap GET that pins the current db into a fresh session.
            http_session = requests.Session()
            session_id = request.httprequest.cookies.get('session_id')
            if session_id:
                http_session.cookies.set('session_id', session_id)
            else:
                bootstrap_url = f"{request.httprequest.host_url.rstrip('/')}/web?db={request.env.cr.dbname}"
                try:
                    http_session.get(bootstrap_url, allow_redirects=False, timeout=15)
                except requests.RequestException as exc:
                    _logger.warning("Bootstrap GET %s failed: %s", bootstrap_url, exc)

            response = http_session.post(webhook_url, json=payload, headers=headers, timeout=60)
            _logger.info(f"Respuesta del webhook: {response.status_code}")

            if response.status_code == 200:
                request.env.cr.commit()
                return self._get_company_info_from_payload(payload)
            else:
                error_msg = f"Error en webhook: {response.status_code} - {response.text}"
                _logger.error(error_msg)
                raise UserError(error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Error de conectividad al llamar webhook: {str(e)}"
            _logger.error(error_msg)
            raise UserError(error_msg)
        except UserError:
            raise
        except Exception as e:
            error_msg = f"Error inesperado al llamar webhook: {str(e)}"
            _logger.error(error_msg)
            raise UserError(error_msg)

    def _get_company_info_from_payload(self, payload):
        try:
            ResCompany = request.env['res.company'].sudo()
            company_id = ResCompany.search([
                '|',
                ('name', '=ilike', payload.get('name', '')),
                ('email', '=ilike', payload.get('email', '')),
            ], limit=1)

            if company_id:
                return {
                    'company_id': company_id.id,
                    'company_name': company_id.name,
                    'company_email': company_id.email,
                    'external_id': company_id.external_id,
                    'bearer_token': company_id.bearer_token,
                }
            company_id = ResCompany.search([
                ('sync_token', '=', payload.get('sync_token')),
            ], limit=1)
            if company_id:
                return {
                    'company_id': company_id.id,
                    'company_name': company_id.name,
                    'company_email': company_id.email,
                    'external_id': company_id.external_id,
                    'bearer_token': company_id.bearer_token,
                }
            raise UserError("No se pudo encontrar la empresa creada/actualizada")

        except Exception as e:
            _logger.error(f"Error obteniendo informacion de empresa: {str(e)}")
            raise
