"""Unit tests for distributor order importers (LCSC, Mouser, DigiKey)."""

import os
import unittest
from stockcheck.importers import import_order_file, detect_importer


class TestImporters(unittest.TestCase):

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sample_dir = os.path.join(self.base_dir, "examples", "sample_orders")

    def test_lcsc_importer(self):
        file_path = os.path.join(self.sample_dir, "lcsc_sample_order.csv")
        importer = detect_importer(file_path)
        self.assertEqual(importer.distributor_name, "LCSC")

        meta, items = importer.parse_file(file_path)
        self.assertEqual(meta["distributor"], "LCSC")
        self.assertEqual(len(items), 10)

        # Check 10k resistor
        r10k = next((i for i in items if i.distributor_sku == "C2040"), None)
        self.assertIsNotNone(r10k)
        self.assertEqual(r10k.category, "resistor")
        self.assertEqual(r10k.value, "10k")
        self.assertEqual(r10k.package, "0805")
        self.assertEqual(r10k.quantity, 100)

        # Check 100nF cap
        c100n = next((i for i in items if i.distributor_sku == "C15849"), None)
        self.assertIsNotNone(c100n)
        self.assertEqual(c100n.category, "capacitor")
        self.assertEqual(c100n.package, "0805")
        self.assertEqual(c100n.quantity, 50)

    def test_mouser_importer(self):
        file_path = os.path.join(self.sample_dir, "mouser_sample_order.csv")
        importer = detect_importer(file_path)
        self.assertEqual(importer.distributor_name, "Mouser")

        meta, items = importer.parse_file(file_path)
        self.assertEqual(meta["distributor"], "Mouser")
        self.assertEqual(len(items), 6)

        stm = next((i for i in items if "STM32F401" in i.mpn), None)
        self.assertIsNotNone(stm)
        self.assertEqual(stm.quantity, 5)

    def test_digikey_importer(self):
        file_path = os.path.join(self.sample_dir, "digikey_sample_order.csv")
        importer = detect_importer(file_path)
        self.assertEqual(importer.distributor_name, "DigiKey")

        meta, items = importer.parse_file(file_path)
        self.assertEqual(meta["distributor"], "DigiKey")
        self.assertEqual(len(items), 6)

        ne555 = next((i for i in items if i.mpn == "NE555P"), None)
        self.assertIsNotNone(ne555)
        self.assertEqual(ne555.quantity, 10)


if __name__ == "__main__":
    unittest.main()
