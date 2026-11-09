"""Unit tests for component value and package normalizer."""

import unittest
from stockcheck.normalizer import (
    parse_resistor_value, parse_capacitor_value, parse_inductor_value,
    format_resistor_value, format_capacitor_value, format_inductor_value,
    normalize_package, packages_match, values_match, clean_mpn, infer_category
)


class TestNormalizer(unittest.TestCase):

    def test_resistor_parsing(self):
        val, fmt = parse_resistor_value("10k")
        self.assertEqual(val, 10000.0)
        self.assertEqual(fmt, "10k")

        val, fmt = parse_resistor_value("4k7")
        self.assertEqual(val, 4700.0)
        self.assertEqual(fmt, "4.7k")

        val, fmt = parse_resistor_value("0R05")
        self.assertEqual(val, 0.05)
        self.assertEqual(fmt, "0.05R")

        val, fmt = parse_resistor_value("1M")
        self.assertEqual(val, 1000000.0)
        self.assertEqual(fmt, "1M")

        val, fmt = parse_resistor_value("0R")
        self.assertEqual(val, 0.0)
        self.assertEqual(fmt, "0R")

    def test_capacitor_parsing_and_equivalence(self):
        v_100n, f_100n = parse_capacitor_value("100nF")
        v_01u, f_01u = parse_capacitor_value("0.1uF")
        
        self.assertTrue(values_match(v_100n, v_01u))
        self.assertEqual(f_100n, "100nF")
        self.assertEqual(f_01u, "100nF")

        v_10p, f_10p = parse_capacitor_value("10pF")
        self.assertEqual(f_10p, "10pF")

        v_10u, f_10u = parse_capacitor_value("10uF")
        self.assertEqual(f_10u, "10uF")

    def test_inductor_parsing(self):
        v, f = parse_inductor_value("10uH")
        self.assertEqual(f, "10uH")

        v_n, f_n = parse_inductor_value("100nH")
        self.assertEqual(f_n, "100nH")

    def test_package_normalization(self):
        self.assertEqual(normalize_package("Resistor_SMD:R_0805_2012Metric"), "0805")
        self.assertEqual(normalize_package("Capacitor_SMD:C_0603_1608Metric"), "0603")
        self.assertEqual(normalize_package("Package_TO_SOT_SMD:SOT-23-3"), "SOT-23")
        self.assertEqual(normalize_package("Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"), "SOIC-8")
        self.assertEqual(normalize_package("Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm"), "QFN-32")

    def test_package_matching(self):
        self.assertTrue(packages_match("0805", "Resistor_SMD:R_0805_2012Metric"))
        self.assertTrue(packages_match("0805", "2012Metric"))
        self.assertTrue(packages_match("SOT-23", "SOT-23-3"))
        self.assertFalse(packages_match("0805", "0603"))

    def test_clean_mpn(self):
        self.assertEqual(clean_mpn("STM32F401CEU6TR"), "STM32F401CEU6")
        self.assertEqual(clean_mpn("CRCW080510K0FKEA-REEL"), "CRCW080510K0FKEA")
        self.assertEqual(clean_mpn("311-10.0KCRCT-ND"), "311-10.0KCRCT")

    def test_category_inference(self):
        self.assertEqual(infer_category(ref="R1"), "resistor")
        self.assertEqual(infer_category(ref="C12"), "capacitor")
        self.assertEqual(infer_category(ref="L2"), "inductor")
        self.assertEqual(infer_category(ref="U1"), "ic")
        self.assertEqual(infer_category(ref="D3"), "diode")
        self.assertEqual(infer_category(ref="Q1"), "transistor")
        self.assertEqual(infer_category(ref="J5"), "connector")


if __name__ == "__main__":
    unittest.main()
