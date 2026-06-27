# coding: utf-8
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Apply LATAM address format defaults."""
    try:
        custom_view = env.ref("solt_l10n_mx_partner_address.mx_partner_address_form")
    except ValueError:
        custom_view = False
        _logger.info("View 'solt_l10n_mx_partner_address.mx_partner_address_form' not found")

    address_format = (
        "%(street_name)s %(street_number)s %(street_number2)s\n"
        "%(l10n_mx_colony)s\n"
        "%(zip)s %(city)s, %(state_name)s\n"
        "%(country_name)s"
    )

    countries = ["base.ar", "base.cl", "base.co"]

    for country_xmlid in countries:
        try:
            country = env.ref(country_xmlid)
            vals = {"address_format": address_format}
            if custom_view:
                vals["address_view_id"] = custom_view.id
            country.write(vals)
            _logger.info(f"Custom address format applied to {country.name} ({country.code})")
        except ValueError:
            _logger.warning(f"Country not found with XMLID {country_xmlid}")

    connector = env.ref('solt_tiendanube.tn_connector_api', raise_if_not_found=False)
    if connector:
        try:
            connector.action_create_all_meta_fields()
            _logger.info("Tiendanube meta-fields created on install.")
        except Exception as meta_error:
            _logger.warning("Could not create Tiendanube meta-fields on install: %s", str(meta_error))
