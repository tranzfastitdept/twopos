import csv
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app


class PosAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        for slug in app.SHOP_SLUGS:
            source = Path(app.__file__).resolve().parent / slug / "data"
            data_dir = self.root / slug / "data"
            data_dir.mkdir(parents=True)
            shutil.copyfile(source / "shops.csv", data_dir / "shops.csv")
            shutil.copyfile(source / "products.csv", data_dir / "products.csv")
            with (data_dir / "transactions.csv").open("w", encoding="utf-8", newline="") as file:
                csv.writer(file).writerow(
                    ["txn_id", "timestamp", "items_json", "total_amount", "payment_method", "amount_paid", "change_given"]
                )
        patcher = patch.object(app, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.temp_dir.cleanup)
        self.client = app.app.test_client()

    def test_register_and_menu_are_available_for_both_shops(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        for slug in app.SHOP_SLUGS:
            self.assertEqual(self.client.get(f"/{slug}/").status_code, 200)
            response = self.client.get(f"/{slug}/api/products")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.get_json()), 6)
        self.assertEqual(app.shop_config("keecoo_pos")[1]["receipt_header"], "Thank you! Happiness, baked chunky.")

    def test_cash_checkout_saves_receipt_and_sales_to_only_its_shop(self):
        response = self.client.post(
            "/workstation_specialty_coffee_pos/api/checkout",
            json={
                "items": [{"product_id": "white-con-leche", "quantity": 2}],
                "payment_method": "Cash",
                "amount_paid": "500.00",
            },
        )
        self.assertEqual(response.status_code, 201)
        order = response.get_json()
        self.assertEqual(order["total_amount"], "320.00")
        self.assertEqual(order["change_given"], "180.00")
        self.assertEqual(order["items"][0]["line_total"], "320.00")
        history = self.client.get("/workstation_specialty_coffee_pos/api/analytics").get_json()
        self.assertEqual(history["gross_sales"], "320.00")
        self.assertEqual(history["cash_sales"], "320.00")
        self.assertEqual(history["order_count"], 1)
        self.assertEqual(self.client.get("/keecoo_pos/api/analytics").get_json()["order_count"], 0)
        self.assertEqual(
            self.client.get(f"/workstation_specialty_coffee_pos/api/transactions/{order['id']}").get_json(),
            order,
        )

    def test_insufficient_cash_and_invalid_products_do_not_write_sales(self):
        url = "/workstation_specialty_coffee_pos/api/checkout"
        insufficient = self.client.post(url, json={
            "items": [{"product_id": "white-con-leche", "quantity": 1}],
            "payment_method": "Cash",
            "amount_paid": "100",
        })
        self.assertEqual(insufficient.status_code, 400)
        invalid_product = self.client.post(url, json={
            "items": [{"product_id": "not-a-menu-item", "quantity": 1}],
            "payment_method": "Digital",
        })
        self.assertEqual(invalid_product.status_code, 400)
        too_many = self.client.post(url, json={
            "items": [{"product_id": "white-con-leche", "quantity": 100}],
            "payment_method": "Digital",
        })
        self.assertEqual(too_many.status_code, 400)
        self.assertEqual(self.client.get("/workstation_specialty_coffee_pos/api/analytics").get_json()["order_count"], 0)

    def test_digital_checkout_uses_catalog_price(self):
        response = self.client.post("/keecoo_pos/api/checkout", json={
            "items": [{"product_id": "ube-royale", "quantity": 1}],
            "payment_method": "Digital",
            "amount_paid": "0",
        })
        self.assertEqual(response.status_code, 201)
        order = response.get_json()
        self.assertEqual(order["total_amount"], "149.00")
        self.assertEqual(order["amount_paid"], "149.00")
        self.assertEqual(order["payment_method"], "Digital")
        self.assertEqual(order["items"][0]["name"], "Ube Royale Keecoo")

    def test_dedicated_register_redirects_home_and_rejects_the_other_shop(self):
        previous_shop = app.app.config["POS_SHOP_SLUG"]
        app.app.config["POS_SHOP_SLUG"] = "keecoo_pos"
        try:
            response = self.client.get("/")
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.headers["Location"].endswith("/keecoo_pos/"))
            dedicated_page = self.client.get("/keecoo_pos/")
            self.assertEqual(dedicated_page.status_code, 200)
            self.assertNotIn("Choose a different shop", dedicated_page.get_data(as_text=True))
            self.assertEqual(self.client.get("/workstation_specialty_coffee_pos/").status_code, 404)
            self.assertEqual(
                self.client.get("/assets/workstation_specialty_coffee_pos/logo/wssc_logo.png").status_code,
                404,
            )
        finally:
            app.app.config["POS_SHOP_SLUG"] = previous_shop


if __name__ == "__main__":
    unittest.main()
