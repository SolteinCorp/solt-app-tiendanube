# Odoo ↔ Tiendanube Connector

**Version:** 17.0.1.0.7  
**Category:** Sales/Multichannel  
**License:** LGPL-3

## Overview / Descripción General

> **Basado en el listado de la app de Tiendanube:** Esta solución oficial conecta Tiendanube con Odoo para centralizar catálogos, pedidos, inventarios y envíos, eliminando tareas manuales y simplificando operaciones omnicanal.
>
> Este conector sincroniza catálogos multicanal (atributos, variantes, imágenes, SEO), importa pedidos de Tiendanube a flujos de venta nativos, envía actualizaciones de cumplimiento (envíos, guías, cancelaciones) y ofrece dashboards con alertas para la toma de decisiones en tiempo real.

El **Soltein Tiendanube Connector** mantiene Odoo 17.0 sincronizado con Tiendanube: productos, imágenes adicionales, precios, inventario, pedidos, envíos y facturas fluyen automáticamente entre ambas plataformas. Los comerciantes multi-empresa pueden orquestar múltiples almacenes, mantener catálogos de marca y automatizar reglas de cumplimiento sin salir de Odoo.

## Key Features / Características Principales

| Feature | Descripción |
| --- | --- |
| **Sincronización bidireccional de catálogo** | Envía plantillas de productos, marcas, múltiples categorías, precios, contenido SEO e imágenes de galería. |
| **Orquestación de inventario** | Publica cifras de stock por almacén, reserva unidades y mantiene la disponibilidad alineada con Tiendanube. |
| **Importación de pedidos** | Importa pedidos, clientes, referencias de pago, cupones y métodos de entrega a órdenes de venta nativas. |
| **Puente logístico** | Activa entregas, actualiza números de rastreo y notifica a Tiendanube vía webhooks seguros. |
| **Automatización de flujos** | Automatizaciones base, cron jobs y webhooks mantienen ambos sistemas alineados sin clics manuales. |
| **Helpers de localización** | Formato de direcciones, unidades de medida y configuraciones regionales diseñadas para tiendas LATAM. |

## Dependency Stack / Arquitectura de Dependencias

| Módulo | Propósito |
| --- | --- |
| `solt_api_connector` | Framework core que modela APIs REST, maneja autenticación, webhooks, schedulers, logs de llamadas y provee el motor de sincronización reutilizable. |
| `sale` | Módulo nativo de Odoo para gestión de órdenes de venta. |
| `sale_stock` | Integración entre ventas e inventario. |
| `stock` | Módulo nativo de Odoo para gestión de inventario. |
| `solt_l10n_mx_partner_address` | Enriquecimiento de direcciones mexicanas para mapear datos de envío de Tiendanube a Odoo. |
| `stock_delivery` | Módulo nativo de Odoo para transportistas y envíos. |

## Modelos Incluidos / Included Models

| Modelo | Propósito |
| --- | --- |
| `product.template` | Extensión para sincronización de productos con Tiendanube |
| `product.product` | Variantes de producto sincronizadas |
| `product.category` | Categorías de producto mapeadas a Tiendanube |
| `sale.order` | Órdenes de venta importadas desde Tiendanube |
| `sale.order.line` | Líneas de pedido con datos de Tiendanube |
| `res.partner` | Clientes sincronizados desde Tiendanube |
| `stock.picking` | Envíos y actualizaciones de tracking |
| `stock.warehouse` | Mapeo de almacenes para sincronización de stock |
| `account.move` | Facturas vinculadas a pedidos de Tiendanube |
| `solt.api.connector` | Configuración del conector API |
| `solt.product.brand` | Marcas de productos para Tiendanube |
| `solt.product.image` | Imágenes adicionales de productos |
| `solt.register.webhook` | Registro y gestión de webhooks |
| `warehouse.sync.mapping` | Mapeo de almacenes para sincronización |

## Requirements / Requisitos

- Odoo 17.0 Community o Enterprise
- Dependencias listadas en `__manifest__.py`
- Credenciales de API válidas de Tiendanube por compañía
- Requisitos de Python heredados de la instalación base de Odoo

## Installation / Instalación

1. Clonar este repositorio dentro del path de addons personalizados.
2. Instalar las dependencias del conector (`solt_api_connector`, helpers de workflow, etc.).
3. Actualizar la lista de Apps e instalar **Odoo ↔ Tiendanube Connector**.
4. Asignar los nuevos grupos de seguridad a usuarios de integración.

## Configuration / Configuración

1. Navegar a **Tiendanube Connector ▸ Settings** e ingresar las API keys / App ID.
2. Configurar endpoints de webhook y activar los eventos requeridos.
3. Mapear almacenes mediante **Tiendanube Connector ▸ Warehouse Mapping**.
4. Habilitar cron jobs según la cadencia de sincronización deseada.
5. Ejecutar sincronización inicial de productos seguida de pulls de stock y pedidos.

## Next Steps Before Publishing / Próximos Pasos

1. Capturar 3–5 screenshots (dashboard, order sync, configuración) y agregarlos a `static/description/` como `screenshot_X.png`.
2. Instalar en una base de datos limpia, ejecutar smoke test y exportar traducciones:
   ```bash
   ./odoo-bin -c odoo.conf -d test_tiendanube --stop-after-init -i solt_tiendanube
   ./odoo-bin -c odoo.conf -d test_tiendanube --i18n-export=solt_tiendanube/i18n/es_MX.po --modules=solt_tiendanube
   ```
3. Empaquetar el módulo:
   ```bash
   cd ..
   zip -r solt_tiendanube_17.0.1.0.7.zip solt_tiendanube -x "*/__pycache__/*" "*.pyc"
   ```
4. Subir en Odoo Apps con screenshots actualizados y categoría `Sales/Multichannel`.

## Support / Soporte

- Website: <https://www.soltein.mx>
- Email: [soporte@soltein.mx](mailto:soporte@soltein.mx)

## License / Licencia

This suite is released under the **LGPL-3** license. See the root `LICENSE` file or <https://www.gnu.org/licenses/lgpl-3.0.en.html> for the complete terms. / Este conjunto se publica bajo licencia **LGPL-3**.
