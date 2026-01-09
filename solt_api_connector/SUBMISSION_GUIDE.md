# API Connector – Odoo App Store Submission Guide

## 1. Pre-flight Checklist

- [x] `__manifest__.py` updated (English summary, maintainer, support, category, assets, images)
- [x] README + LICENSE + CHANGELOG + landing page created
- [x] Icons (`icon.png`, `icon_module.png`) present
- [x] Source strings in English (translate Python/XML before packaging)
- [ ] Screenshots (PNG, 1280×720) added to `static/description/`
- [ ] Translation exported to `i18n/es_MX.po`
- [ ] Tested on clean database

## 2. Testing Commands

```bash
# Install in fresh DB
./odoo-bin -c odoo.conf -d test_api_connector \
  -i solt_api_connector --stop-after-init

# Run tests (if applicable)
./odoo-bin -c odoo.conf -d test_api_connector \
  -i solt_api_connector --test-enable --stop-after-init
```

## 3. Translation Export

```bash
./odoo-bin -c odoo.conf -d prod_db \
  --i18n-export=solt_api_connector/i18n/es_MX.po \
  --modules=solt_api_connector --log-level=warn
```

## 4. Packaging

```bash
zip -r solt_api_connector_18.0.1.0.1.zip solt_api_connector \
  -x "*/__pycache__/*" "*.pyc" "*.pyo" "*/.git/*"
```

Verify zip contents:

```bash
unzip -l solt_api_connector_18.0.1.0.1.zip
```

## 5. App Store Form

- **Module name**: API Connector
- **Summary**: Configurable API orchestration framework for Odoo 18
- **Version**: 18.0.1.0.1
- **License**: LGPL-3 (attach LICENSE)
- **Category**: Tools/Connectivity
- **Tags**: API, Integration, Automation, Connector
- **Support email**: soporte@soltein.mx
- **Website**: https://www.soltein.mx
- **Maintainers**: soltein
- **Screenshots**: upload the PNGs referenced in landing page

## 6. Post-submission

- Track review feedback inside Odoo Apps dashboard
- Respond to reviewer comments (licensing, dependencies, documentation)
- Publish updates via version bump + changelog entry

