# -*- coding: utf-8 -*-
# Copyright 2024 Soltein SA. de CV.
# License LGPL-3 or later (http://www.gnu.org/licenses/lgpl.html)
import json
import logging
from datetime import timedelta

import requests as http_requests

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

# HTTP codes that indicate a transient error — safe to retry
_RETRY_CODES = frozenset({0, 408, 429, 500, 502, 503, 504})
# HTTP codes that indicate a permanent/data error — never retry
_NO_RETRY_CODES = frozenset({400, 401, 403, 404, 405, 422})


class SoltApiCallLog(models.Model):
    _name = 'solt.api.call.log'
    _description = 'API Call Log'
    _order = 'create_date desc'

    # ------------------------------------------------------------------
    # Base fields
    # ------------------------------------------------------------------
    connector_id = fields.Many2one('solt.api.connector', string='API Connector', required=True, ondelete='cascade')
    endpoint_id = fields.Many2one('solt.api.endpoint', string='Endpoint', ondelete='set null')

    request_url = fields.Char('Request URL', readonly=True)
    request_method = fields.Char('HTTP method', readonly=True)
    request_headers = fields.Text('Request headers', readonly=True)
    request_params = fields.Text('Request parameters', readonly=True)
    request_body = fields.Text('Request payload', readonly=True)

    response_code = fields.Integer('Response code', readonly=True)
    response_headers = fields.Text('Response headers', readonly=True,
                                   help="HTTP response headers stored as JSON. "
                                        "Used by the retry system to read rate-limit hints (e.g. x-rate-limit-reset).")
    response_body = fields.Text('Response payload', readonly=True)

    duration = fields.Float('Duration (s)', digits=(10, 3), readonly=True)
    success = fields.Boolean('Successful', default=False, readonly=True)

    name = fields.Char('Name', compute='_compute_name', store=True, readonly=True)
    automation_id = fields.Many2one('base.automation', string='Automation', ondelete='set null', readonly=True,
                                    help="Related automation if this call was triggered by one.")
    company_id = fields.Many2one('res.company', string='Company', readonly=True,
                                 help="Related company if this call was triggered by one.")
    direction = fields.Selection(
        [('outgoing', 'Outgoing'), ('incoming', 'Incoming')],
        string='Direction',
        default='outgoing',
        readonly=True,
        help="Direction of the API call: 'Outgoing' if initiated by Odoo to an external API, "
             "'Incoming' if received from an external source (e.g. webhook)."
    )

    # ------------------------------------------------------------------
    # Record tracing — the Odoo record that triggered this call
    # ------------------------------------------------------------------
    res_model_id = fields.Many2one(
        'ir.model', string='Related model',
        readonly=True, ondelete='set null',
        help="Odoo model of the record that originated this API call."
    )
    res_id = fields.Integer(
        'Record ID', readonly=True,
        help="ID of the Odoo record that originated this API call."
    )

    # ------------------------------------------------------------------
    # Retry fields
    # ------------------------------------------------------------------
    retry_state = fields.Selection([
        ('pending', 'Pending'),
        ('retrying', 'Retrying'),
        ('resolved', 'Resolved'),
        ('exhausted', 'Exhausted'),
    ], string='Retry state', readonly=True, index=True,
        help="Current state of the automatic retry process for this log.")
    retry_count = fields.Integer('Retries done', default=0, readonly=True,
                                 help="Number of retry attempts executed so far.")
    max_retries = fields.Integer('Max retries', default=0, readonly=True,
                                 help="Maximum retries allowed, copied from the connector at log creation.")
    next_retry_at = fields.Datetime('Next retry at', readonly=True,
                                    help="Scheduled datetime for the next retry attempt.")
    is_retry = fields.Boolean('Is a retry', default=False, readonly=True,
                               help="True when this log was created by the retry cron (child log).")
    original_log_id = fields.Many2one(
        'solt.api.call.log', string='Original log',
        ondelete='cascade', readonly=True, index=True,
        help="The original failed log that triggered the retry chain."
    )
    child_log_ids = fields.One2many(
        'solt.api.call.log', 'original_log_id',
        string='Retry attempts',
        help="Child logs created by each retry attempt."
    )

    # ------------------------------------------------------------------
    # Computed name
    # ------------------------------------------------------------------
    @api.depends('create_date', 'endpoint_id', 'automation_id', 'request_method', 'direction')
    def _compute_name(self):
        for record in self:
            if record.create_date:
                date_str = fields.Datetime.to_string(record.create_date)
                if record.endpoint_id:
                    label = record.endpoint_id.name
                elif record.automation_id:
                    label = record.automation_id.name
                else:
                    label = _('Unknown endpoint')
                http_method = record.request_method or ('POST' if record.direction == 'incoming' else 'GET')
                record.name = f"{date_str} - {http_method} {label}"
            else:
                record.name = _('New API call')

    # ------------------------------------------------------------------
    # Retry initialisation (called from execute_request on failure)
    # ------------------------------------------------------------------
    def _init_retry_if_needed(self):
        """Called just after log creation on a failed outgoing call.
        Sets the retry fields if the connector has retries enabled and the
        response code is eligible for retry."""
        self.ensure_one()
        connector = self.connector_id
        if not connector.retry_enabled:
            return
        if self.success or self.direction != 'outgoing' or self.is_retry:
            return
        if not self._should_retry(self.response_code):
            return
        self.write({
            'retry_state': 'pending',
            'retry_count': 0,
            'max_retries': connector.max_retry_count or 3,
            # source_log=self so connectors can read self.response_headers for hints (e.g. 429)
            'next_retry_at': self._compute_next_retry_at(self.response_code, retry_count=0, source_log=self),
        })

    def _should_retry(self, response_code):
        """Returns True if the response code warrants an automatic retry.
        Override in connector-specific modules to add or remove codes."""
        if response_code in _NO_RETRY_CODES:
            return False
        return response_code in _RETRY_CODES

    def _compute_next_retry_at(self, response_code, retry_count, source_log=None):
        """Computes the datetime for the next retry attempt.

        :param response_code: HTTP status code of the failed response.
        :param retry_count:   Number of attempts already done (0-based for the
                              first scheduled retry).
        :param source_log:    The log record whose response_headers may contain
                              API hints (e.g. x-rate-limit-reset). For the initial
                              failure this is the original log itself; for subsequent
                              failures it is the child log created by the cron.
        :returns: datetime for the next retry.

        Override in connector-specific modules to read rate-limit headers or
        apply any other custom scheduling logic.
        """
        connector = self.connector_id
        base_delay = connector.retry_delay_minutes or 5
        if connector.retry_strategy == 'exponential':
            delay_min = base_delay * (2 ** retry_count)
        else:
            delay_min = base_delay
        return fields.Datetime.now() + timedelta(minutes=delay_min)

    # ------------------------------------------------------------------
    # Cron entry point
    # ------------------------------------------------------------------
    @api.model
    def cron_process_pending_retries(self):
        """Cron job: finds all outgoing original logs in *pending* state
        whose next_retry_at is in the past and executes each retry inside
        its own savepoint so one failure does not affect the others."""
        now = fields.Datetime.now()
        pending = self.search([
            ('retry_state', '=', 'pending'),
            ('next_retry_at', '<=', now),
            ('direction', '=', 'outgoing'),
            ('is_retry', '=', False),
        ])
        _logger.info("Retry cron: %d log(s) to process.", len(pending))
        for log in pending:
            try:
                with self.env.cr.savepoint():
                    log._process_single_retry()
            except Exception as exc:
                _logger.error(
                    "Retry cron: unhandled error processing log %d: %s", log.id, exc
                )

    # ------------------------------------------------------------------
    # Per-log retry logic
    # ------------------------------------------------------------------
    def _process_single_retry(self):
        self.ensure_one()
        self.write({'retry_state': 'retrying'})
        child_log = self._execute_retry_request()
        if child_log.success:
            self.write({'retry_state': 'resolved'})
        else:
            # Pass child_log so _compute_next_retry_at can read its response_headers
            self._handle_retry_failure(child_log.response_code, child_log=child_log)

    def _execute_retry_request(self):
        """Re-sends the stored HTTP request and creates a child log record."""
        self.ensure_one()
        headers = json.loads(self.request_headers) if self.request_headers else {}
        params = json.loads(self.request_params) if self.request_params else {}
        body = json.loads(self.request_body) if self.request_body else None
        method = (self.request_method or 'GET').upper()
        timeout = self.connector_id.timeout or 30

        child_vals = {
            'connector_id': self.connector_id.id,
            'endpoint_id': self.endpoint_id.id,
            'company_id': self.company_id.id,
            'direction': 'outgoing',
            'request_url': self.request_url,
            'request_method': self.request_method,
            'request_headers': self.request_headers,
            'request_params': self.request_params,
            'request_body': self.request_body,
            'is_retry': True,
            'original_log_id': self.id,
            'res_model_id': self.res_model_id.id or False,
            'res_id': self.res_id,
        }

        start = fields.Datetime.now()
        try:
            kwargs = {'params': params, 'headers': headers, 'timeout': timeout}
            if method in ('POST', 'PUT', 'PATCH'):
                kwargs['json'] = body
            response = getattr(http_requests, method.lower())(self.request_url, **kwargs)
            end = fields.Datetime.now()
            child_vals.update({
                'response_code': response.status_code,
                'response_headers': json.dumps(dict(response.headers)),
                'response_body': response.text,
                'success': 200 <= response.status_code < 300,
                'duration': (end - start).total_seconds(),
            })
        except Exception as exc:
            end = fields.Datetime.now()
            child_vals.update({
                'response_code': 0,
                'response_body': str(exc),
                'success': False,
                'duration': (end - start).total_seconds(),
            })

        return self.env['solt.api.call.log'].create(child_vals)

    def _handle_retry_failure(self, response_code, child_log=None):
        """Increments the retry counter and either schedules the next attempt
        or marks the log as exhausted.

        :param child_log: The child log created by this retry attempt.
                          Passed to _compute_next_retry_at so connector-specific
                          overrides can inspect its response_headers."""
        self.ensure_one()
        new_count = self.retry_count + 1
        if new_count >= self.max_retries:
            self.write({'retry_state': 'exhausted', 'retry_count': new_count})
        else:
            self.write({
                'retry_state': 'pending',
                'retry_count': new_count,
                'next_retry_at': self._compute_next_retry_at(
                    response_code, retry_count=new_count, source_log=child_log
                ),
            })
