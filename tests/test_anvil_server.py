import importlib
import sys
import types
import unittest
from pathlib import Path


class FakeRow(dict):
    pass


class FakeTable:
    def __init__(self):
        self.rows = []

    def get(self, **criteria):
        return next(
            (row for row in self.rows if all(row.get(key) == value for key, value in criteria.items())),
            None,
        )

    def add_row(self, **values):
        row = FakeRow(values)
        self.rows.append(row)
        return row

    def search(self, **criteria):
        return [
            row for row in self.rows
            if all(row.get(key) == value for key, value in criteria.items())
        ]


class FakeTables:
    def __init__(self):
        self.shops = FakeTable()
        self.products = FakeTable()
        self.transactions = FakeTable()
        self.app_settings = FakeTable()


tables_store = FakeTables()


def _install_anvil_stubs():
    anvil = types.ModuleType("anvil")
    anvil.__path__ = []
    anvil_tables = types.ModuleType("anvil.tables")
    anvil_tables.app_tables = tables_store
    anvil_tables.in_transaction = lambda function: function
    anvil_server = types.ModuleType("anvil.server")
    anvil_server.callable = lambda function: function
    anvil.tables = anvil_tables
    anvil.server = anvil_server
    sys.modules.update({
        "anvil": anvil,
        "anvil.tables": anvil_tables,
        "anvil.server": anvil_server,
    })


_install_anvil_stubs()
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
server = importlib.import_module("server_code.ServerModule1")


class AnvilServerTests(unittest.TestCase):
    def setUp(self):
        for table in (
            tables_store.shops,
            tables_store.products,
            tables_store.transactions,
            tables_store.app_settings,
        ):
            table.rows.clear()

    def test_seeded_catalog_and_completed_order_are_shop_scoped(self):
        initial = server.get_initial_data()
        self.assertIsNone(initial["default_shop"])
        self.assertEqual(len(initial["shops"]), 2)
        self.assertEqual(len(server.get_products_by_shop("workstation_specialty_coffee_pos")), 6)
        self.assertEqual(len(server.get_products_by_shop("keecoo_pos")), 6)

        order = server.submit_transaction(
            "keecoo_pos",
            [{"product_id": "ube-royale", "quantity": 1}],
            "Cash",
            "200",
        )
        self.assertEqual(order["total_amount"], 149.0)
        self.assertEqual(order["change_given"], 51.0)
        self.assertEqual(
            server.get_shop_analytics("keecoo_pos")["gross_sales"],
            "₱149.00",
        )
        self.assertEqual(server.get_shop_analytics("workstation_specialty_coffee_pos")["order_count"], 0)

    def test_invalid_and_insufficient_checkouts_do_not_write_transactions(self):
        server.get_initial_data()
        cases = [
            ("keecoo_pos", [{"product_id": "ube-royale", "quantity": 1}], "Cash", "100"),
            ("keecoo_pos", [{"product_id": "white-con-leche", "quantity": 1}], "Digital", "0"),
            ("keecoo_pos", [{"product_id": "ube-royale", "quantity": 100}], "Digital", "0"),
        ]
        for args in cases:
            with self.assertRaises(ValueError):
                server.submit_transaction(*args)
        self.assertEqual(len(tables_store.transactions.rows), 0)

    def test_default_shop_setting_restricts_the_deployment(self):
        server.get_initial_data()
        settings = tables_store.app_settings.get(key="default_shop")
        settings["value"] = "keecoo_pos"
        initial = server.get_initial_data()
        self.assertEqual(initial["default_shop"], "keecoo_pos")
        self.assertEqual([shop["slug"] for shop in initial["shops"]], ["keecoo_pos"])
        with self.assertRaises(ValueError):
            server.get_products_by_shop("workstation_specialty_coffee_pos")


if __name__ == "__main__":
    unittest.main()
