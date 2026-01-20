# solt-tiendanube

Odoo ↔ Tiendanube Connector for Odoo 19.0

## Description

This repository contains the **Soltein Tiendanube Connector** - a bi-directional integration between Odoo 19.0 and Tiendanube that synchronizes catalogs, orders, fulfillment and webhooks.

The connector centralizes product data, pricing, stock availability and shipment statuses for multi-warehouse sellers, eliminating manual tasks and simplifying omnichannel operations.

## Features

- **Two-way catalog sync** – Push product templates, brands, multi categories, prices, SEO content, and gallery images
- **Product brand management** – Create and maintain custom brand dictionaries consumed by Tiendanube listings
- **Multi-category tagging** – Assign additional product categories required by Tiendanube storefronts
- **Multi-warehouse orders** – Split sales fulfillment by warehouse with per-line delivery dates and routing
- **Inventory orchestration** – Publish stock figures per warehouse, reserve units, and keep availability aligned
- **Order intake** – Import orders, customers, payment references, coupons, and delivery methods
- **Logistics bridge** – Trigger deliveries, update tracking numbers, and notify Tiendanube via secure webhooks
- **Workflow automation** – Base automations, cron jobs, and webhooks keep both systems aligned
- **Localization helpers** – Address formatting, measurement units, and regional settings for LATAM stores

## Module Structure

```
solt-tiendanube/
└── solt_tiendanube/          # Main connector module
    ├── models/               # Business logic (products, orders, brands, etc.)
    ├── views/                # XML views and menus
    ├── security/             # Access rights and record rules
    ├── data/                 # Default data, crons, endpoints
    ├── controllers/          # HTTP controllers for webhooks
    ├── static/               # Assets and module description
    └── i18n/                 # Translations
```

## Dependencies

| Module | Purpose |
| --- | --- |
| `solt_api_connector` | Core API framework for REST APIs, authentication, webhooks, and sync engine |
| `solt_l10n_mx_partner_address` | Mexican address enrichment for shipping data |
| `sale`, `sale_stock`, `stock`, `stock_delivery` | Native Odoo models for orders, inventory, and shipments |

## Requirements

- Odoo 19.0 Community or Enterprise
- Valid Tiendanube API credentials per company
- Python requirements inherited from base Odoo installation

## Installation

1. Clone this repository inside your custom addons path
2. Install dependencies (`solt_api_connector`, `solt_l10n_mx_partner_address`)
3. Update the Apps list and install **Odoo ↔ Tiendanube Connector**
4. Assign security groups to integration users

## Configuration

1. Navigate to **Tiendanube Connector ▸ Settings** and enter API keys
2. Configure webhook endpoints and activate required events
3. Map warehouses through **Tiendanube Connector ▸ Warehouse Mapping**
4. Enable multi-warehouse orders in **Sales ▸ Settings** if needed
5. Enable cron jobs for your synchronization cadence
6. Run initial product sync followed by stock and order pulls

## Support

- Website: https://www.soltein.mx
- Email: soporte@soltein.mx

## License

This module is released under the **LGPL-3** license. See the `LICENSE` file for details.
