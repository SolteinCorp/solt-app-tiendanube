# -*- coding: utf-8 -*-
import json
import logging
from datetime import timedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Tiendanube-specific retry code classification
# Codes taken from the official TN API documentation.
# -----------------------------------------------------------------------

# Transient errors — safe to retry automatically
_TN_RETRY_CODES = frozenset({
    429,   # Too Many Requests — rate limit hit; use x-rate-limit-reset header
    500,   # Internal Server Error — TN doc says "retry your request later"
    502,   # Bad Gateway — transient infrastructure error
    503,   # Service Unavailable — transient infrastructure error
    504,   # Gateway Timeout — transient network/infrastructure error
    0,     # Connection error / timeout on our side
})

# Permanent errors — retrying will always produce the same result
_TN_NO_RETRY_CODES = frozenset({
    400,   # Bad Request — invalid JSON or missing User-Agent header
    402,   # Payment Required — store subscription not active or app not paid; needs human action
    404,   # Not Found — resource does not exist
    415,   # Unsupported Media Type — missing Content-Type: application/json; client config error
    422,   # Unprocessable Entity — invalid fields in the body; payload must be corrected
    401,   # Unauthorized — invalid token; requires re-authentication
    403,   # Forbidden — insufficient permissions; requires re-authentication or scope change
})


class SoltApiCallLogTiendanube(models.Model):
    _inherit = 'solt.api.call.log'

    def _should_retry(self, response_code):
        """Tiendanube-specific classification of retryable HTTP codes.

        Overrides the generic implementation with codes documented in the
        official TiendaNube API reference."""
        if response_code in _TN_NO_RETRY_CODES:
            return False
        return response_code in _TN_RETRY_CODES

    def _compute_next_retry_at(self, response_code, retry_count, source_log=None):
        """Computes the next retry datetime, with special handling for 429.

        When TiendaNube responds with HTTP 429 (Too Many Requests) it includes
        the header x-rate-limit-reset whose value is the number of milliseconds
        until the rate-limit bucket resets completely.  We use that value
        directly instead of applying the configured backoff formula, which
        respects the API contract and avoids unnecessary wait time.

        For all other retryable codes the base backoff strategy is used.
        """
        if response_code == 429 and source_log:
            next_retry = self._parse_rate_limit_reset(source_log)
            if next_retry:
                _logger.info(
                    "Log %d: 429 received — scheduling next retry at %s "
                    "(from x-rate-limit-reset header).",
                    self.id, next_retry,
                )
                return next_retry

        return super()._compute_next_retry_at(response_code, retry_count, source_log)

    def _parse_rate_limit_reset(self, source_log):
        """Reads x-rate-limit-reset from the stored response headers of
        *source_log* and returns the corresponding datetime, or False if the
        header is absent or cannot be parsed.

        The TN API expresses this value in **milliseconds** until the bucket
        is empty (not an epoch timestamp)."""
        if not source_log or not source_log.response_headers:
            return False
        try:
            headers = json.loads(source_log.response_headers)
            reset_ms = headers.get('x-rate-limit-reset')
            if reset_ms is None:
                return False
            return fields.Datetime.now() + timedelta(milliseconds=int(reset_ms))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            _logger.warning(
                "Log %d: could not parse x-rate-limit-reset header: %s", self.id, exc
            )
            return False
