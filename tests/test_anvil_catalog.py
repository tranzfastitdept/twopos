import csv
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("anvil_catalog", ROOT / "server_code" / "catalog.py")
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)


class AnvilCatalogTests(unittest.TestCase):
    def test_anvil_catalog_matches_both_csv_menus(self):
        for slug in ("workstation_specialty_coffee_pos", "keecoo_pos"):
            with (ROOT / slug / "data" / "products.csv").open(encoding="utf-8-sig", newline="") as file:
                csv_products = list(csv.DictReader(file))
            anvil_products = catalog.PRODUCTS[slug]
            self.assertEqual(len(anvil_products), len(csv_products))
            for csv_product, anvil_product in zip(csv_products, anvil_products):
                self.assertEqual(anvil_product["product_id"], csv_product["id"])
                self.assertEqual(anvil_product["name"], csv_product["name"])
                self.assertEqual(anvil_product["description"], csv_product["description"])
                self.assertEqual(float(anvil_product["price"]), float(csv_product["price"]))
                self.assertTrue((ROOT / "theme" / "assets" / anvil_product["image"].removeprefix("_/theme/")).is_file())


if __name__ == "__main__":
    unittest.main()
