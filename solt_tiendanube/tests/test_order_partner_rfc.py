# -*- coding: utf-8 -*-
"""Importing a Tiendanube order never rewrites the RFC or the address of an existing partner."""

from odoo.tests import TransactionCase, tagged

ORDER_ADDRESS_FIELDS = (
    "street_name",
    "street_number",
    "street_number2",
    "zip",
    "city_id",
    "city",
    "state_id",
    "country_id",
    "l10n_mx_locality_id",
    "l10n_mx_locality",
)


@tagged("post_install", "-at_install")
class TestOrderPartnerRfc(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env["res.partner"]
        cls.acme = cls.partner_model.create({
            "name": "Acme Prueba",
            "is_company": True,
            "vat": "APR010101AB1",
            "street2": "Nave 2",
            "country_id": cls.env.ref("base.mx").id,
        })
        cls.juan = cls.partner_model.create({
            "name": "Juan Prueba",
            "parent_id": cls.acme.id,
            "type": "contact",
            "email": "juan@prueba.mx",
        })

    def _customer(self, name, email, identification):
        """The customer block of an order, as the Tiendanube API sends it."""
        return {
            "id": f"tn-{email}",
            "name": name,
            "email": email,
            "identification": identification,
            "phone": "",
            "note": "",
            "default_address": {
                "name": name,
                "address": "Calle Prueba",
                "floor": "1",
                "number": "A",
                "zipcode": "20000",
                "locality": "Centro",
                "city": "Aguascalientes",
                "province": "Aguascalientes",
                "country": "MX",
            },
        }

    def _import(self, customer, shipping_address=None):
        """Find or create the contact, delivery and invoice partners of an order, as its import does."""
        return self.partner_model._find_or_create_partners_from_data(customer, shipping_address)

    def _order_address(self, customer):
        """The address a first order of ``customer`` gives the contact it creates."""
        first_contact, _delivery, _invoice = self._import(customer)
        return {
            field_name: first_contact[field_name].id if first_contact._fields[field_name].type == "many2one" else first_contact[field_name]
            for field_name in ORDER_ADDRESS_FIELDS
        }

    def test_a_company_contact_ordering_with_its_own_rfc_gets_a_customer_of_its_own(self):
        contact, _delivery, _invoice = self._import(self._customer("Juan Prueba", "juan@prueba.mx", "PEJU800101AB1"))

        self.assertNotEqual(contact, self.juan)
        self.assertFalse(contact.parent_id)
        self.assertEqual(contact.vat, "PEJU800101AB1")
        self.assertEqual((self.acme.vat, self.juan.vat), ("APR010101AB1", "APR010101AB1"))

    def test_a_customer_ordering_with_another_rfc_keeps_its_own(self):
        pedro, _delivery, _invoice = self._import(self._customer("Pedro Prueba", "pedro@prueba.mx", "PEJU800101AB1"))

        contact, _delivery, _invoice = self._import(self._customer("Pedro Prueba", "pedro@prueba.mx", "PEPE800101XY1"))

        self.assertNotEqual(contact, pedro)
        self.assertEqual((contact.vat, pedro.vat), ("PEPE800101XY1", "PEJU800101AB1"))

    def test_an_order_without_identification_keeps_the_customer_rfc(self):
        pedro, _delivery, _invoice = self._import(self._customer("Pedro Prueba", "pedro@prueba.mx", "PEJU800101AB1"))

        contact, _delivery, _invoice = self._import(self._customer("Pedro Prueba", "pedro@prueba.mx", ""))

        self.assertEqual(contact, pedro)
        self.assertEqual(pedro.vat, "PEJU800101AB1")

    def test_an_order_shipped_to_the_company_address_leaves_the_company_alone(self):
        self.acme.write(self._order_address(self._customer("Juan Prueba", "otro@prueba.mx", "APR010101AB1")))
        shipping_address = {"customs": {"reference": "Porton negro", "between_streets": "Calle A y Calle B"}}

        self._import(self._customer("Juan Prueba", "juan@prueba.mx", "APR010101AB1"), shipping_address)

        self.assertEqual((self.acme.street2, self.juan.street2), ("Nave 2", "Nave 2"))

    def test_a_customer_shipping_to_its_own_address_keeps_its_street2(self):
        luis, _delivery, _invoice = self._import(self._customer("Luis Prueba", "luis@prueba.mx", "PULU800101AB1"))
        luis.street2 = "Interior 4"

        self._import(self._customer("Luis Prueba", "luis@prueba.mx", "PULU800101AB1"))

        self.assertEqual(luis.street2, "Interior 4")
