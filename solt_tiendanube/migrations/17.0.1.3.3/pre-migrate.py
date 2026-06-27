# coding: utf-8
"""Unlock the Tiendanube connector and endpoint records for updates.

These records were loaded with noupdate="1", so later changes to
endpoints_tiendanube_data.xml (such as the marketplace install URL) were never
propagated on upgrade. The data file is now noupdate="0"; this migration clears
the stored noupdate flag on the existing records so the upgrade refreshes them.
"""


def migrate(cr, version):
    cr.execute(
        """
        UPDATE ir_model_data
        SET noupdate = false
        WHERE module = 'solt_tiendanube'
          AND model IN ('solt.api.connector', 'solt.api.endpoint')
        """
    )
