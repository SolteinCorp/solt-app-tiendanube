"""Reset the endpoint form view to its current English arch.

Clears ``arch_prev`` and drops every non-English value of ``arch_db`` for
``solt_api_connector.view_solt_api_endpoint_form``. Odoo loads the module
translations right after the post-migration step of the same upgrade, so each
language is rebuilt from the module's .po files.
"""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """Clear the endpoint form's previous arch and keep only its English arch."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    env.flush_all()
    cr.execute(
        """
        UPDATE ir_ui_view
        SET arch_prev = NULL,
            arch_db = jsonb_build_object('en_US', arch_db -> 'en_US')
        WHERE id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE module = 'solt_api_connector'
              AND name = 'view_solt_api_endpoint_form'
              AND model = 'ir.ui.view'
        )
        """
    )
    env["ir.ui.view"].invalidate_model(["arch_db", "arch_prev"])
