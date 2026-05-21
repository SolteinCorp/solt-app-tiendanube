# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def uninstall_hook(env):
    """Elimina todas las vistas dinámicas creadas por solt_api_connector al desinstalar.

    Las vistas dinámicas (form, list, search) generadas por make_views() quedan
    almacenadas en ir.ui.view con referencia a solt.api.meta.fields. Si el módulo
    se desinstala sin limpiar estas vistas, pueden quedar huérfanas en la BD y
    provocar errores de ParseError en deploys posteriores donde el módulo no esté
    disponible en el addons path.
    """
    _logger.info("solt_api_connector: ejecutando uninstall_hook — limpiando vistas dinámicas huérfanas...")

    meta_fields = env['solt.api.meta.fields'].search([])
    _logger.info("solt_api_connector: encontrados %d registros de solt.api.meta.fields", len(meta_fields))

    for mf in meta_fields:
        model_label = mf.model or '(sin modelo)'

        # Vista de búsqueda — la más crítica: contiene group_by: x_state_sync
        if mf.extended_search_view_id:
            _logger.info(
                "solt_api_connector: eliminando vista de búsqueda dinámica '%s' para modelo '%s'",
                mf.extended_search_view_id.name, model_label,
            )
            mf.action_remove_search_view()

        # Vista de formulario
        if mf.extended_form_view_id:
            _logger.info(
                "solt_api_connector: eliminando vista de formulario dinámica '%s' para modelo '%s'",
                mf.extended_form_view_id.name, model_label,
            )
            mf.action_remove_form_view()

        # Vista de lista
        if mf.extended_list_view_id:
            _logger.info(
                "solt_api_connector: eliminando vista de lista dinámica '%s' para modelo '%s'",
                mf.extended_list_view_id.name, model_label,
            )
            mf.action_remove_list_view()

    _logger.info("solt_api_connector: uninstall_hook completado.")

