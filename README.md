[![Pre-commit Status](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)

<!-- /!\ do not modify above this line -->

# solt-app-tiendanube

Módulos de integración con Tiendanube para Odoo.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

## Addons disponibles

addon | version    | maintainers | summary
--- |------------| --- | ---
[solt_api_connector](solt_api_connector/) | 18.0.1.0.0 |  | Conector base para integraciones de API
[solt_l10n_mx_partner_address](solt_l10n_mx_partner_address/) | 18.0.1.0.0 |  | Localización México - Direcciones de contacto
[solt_multiwarehouse_orders](solt_multiwarehouse_orders/) | 18.0.1.0.0 |  | Gestión de órdenes multi-almacén
[solt_product_brand](solt_product_brand/) | 18.0.1.0.0 |  | Gestión de marcas de productos
[solt_product_multi_category](solt_product_multi_category/) | 18.0.1.0.0 |  | Soporte para múltiples categorías por producto
[solt_tiendanube](solt_tiendanube/) | 18.0.1.0.0 |  | Integración completa con Tiendanube

[//]: # (end addons)

<!-- prettier-ignore-end -->

## Pre-commit

Este repositorio utiliza [pre-commit](https://pre-commit.com/) para ejecutar validaciones automáticas antes de cada commit, asegurando la calidad y consistencia del código.

### Instalación

1. Instala pre-commit y configura los hooks en tu repositorio local:
```bash
   pip install pre-commit
   pre-commit install
```

2. (Opcional) Para actualizar los hooks a sus últimas versiones:
```bash
   pre-commit autoupdate
```

   O para actualizar un repositorio específico:
```bash
   pre-commit autoupdate --repo https://github.com/pre-commit/pre-commit-hooks
```

### Uso

Una vez instalado, pre-commit se ejecutará automáticamente en cada `git commit`. Si alguna validación falla:

- El commit será bloqueado
- Se mostrarán los errores encontrados
- Algunos hooks corregirán los archivos automáticamente

Después de corregir los errores (o si fueron corregidos automáticamente), vuelve a añadir los archivos modificados y realiza el commit nuevamente:
```bash
git add .
git commit -m "tu mensaje"
```

Para ejecutar las validaciones manualmente en todos los archivos:
```bash
pre-commit run --all-files
```

## Licencias

Este repositorio está licenciado bajo [AGPL-3.0](LICENSE).

Sin embargo, cada módulo puede tener una licencia totalmente diferente. Consulte el archivo `__manifest__.py` de cada módulo, que contiene una clave `license` que explica su licencia.

----

Desarrollado por [Soltein SA de CV](https://soltein.mx/)
