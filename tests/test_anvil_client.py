import importlib
import sys
import types
import unittest
from datetime import datetime

from test_anvil_server import server, tables_store


class FakeComponent:
    def __init__(self, **properties):
        self.children = []
        self.events = {}
        self.__dict__.update(properties)

    def add_component(self, component):
        self.children.append(component)

    def clear(self):
        self.children.clear()

    def set_event_handler(self, event_name, handler):
        self.events[event_name] = handler

    def trigger(self, event_name):
        self.events[event_name](sender=self)

    def init_components(self, **properties):
        self.children = []
        self.events = {}
        self.__dict__.update(properties)


def _server_call(function_name, *args):
    return getattr(server, function_name)(*args)


anvil = sys.modules["anvil"]
anvil.server.call = _server_call
anvil.alert = lambda *args, **kwargs: False
anvil.Notification = lambda *args, **kwargs: FakeComponent()
anvil.js = types.ModuleType("anvil.js")
anvil.js.window = types.SimpleNamespace(print=lambda: None)
sys.modules["anvil.js"] = anvil.js
for component_name in ("Button", "ColumnPanel", "FlowPanel", "Image", "Label", "RadioButton", "TextBox"):
    setattr(anvil, component_name, FakeComponent)

designer = types.ModuleType("client_code.MainForm._anvil_designer")
designer.MainFormTemplate = FakeComponent
sys.modules[designer.__name__] = designer
main_form_module = importlib.import_module("client_code.MainForm")
MainForm = main_form_module.MainForm


def find_component(parent, role):
    if getattr(parent, "role", None) == role:
        return parent
    for child in getattr(parent, "children", []):
        result = find_component(child, role)
        if result is not None:
            return result
    return None


class AnvilClientTests(unittest.TestCase):
    def setUp(self):
        for table in (
            tables_store.shops,
            tables_store.products,
            tables_store.transactions,
            tables_store.app_settings,
        ):
            table.rows.clear()
        self.form = MainForm()

    def test_cash_amount_parser_rejects_invalid_values(self):
        self.assertEqual(self.form.parse_cash_amount("125.50"), 125.5)
        self.assertEqual(self.form.parse_cash_amount(""), 0)
        self.assertEqual(self.form.parse_cash_amount("1.2.3"), 0)
        self.assertEqual(self.form.parse_cash_amount("-10"), 0)

    def test_shop_picker_selects_each_shop_and_add_buttons_keep_their_product(self):
        choices = find_component(self.form.root, "shop-choices")
        first_card, second_card = choices.children
        first_card.children[-1].trigger("click")
        self.assertEqual(self.form.current_shop["slug"], "workstation_specialty_coffee_pos")
        self.assertEqual(len(self.form.products), 6)

        self.form.show_shop_picker()
        choices = find_component(self.form.root, "shop-choices")
        choices.children[1].children[-1].trigger("click")
        cards = find_component(self.form.root, "product-grid").children
        cards[0].children[-1].trigger("click")
        cards[1].children[-1].trigger("click")
        self.assertEqual(self.form.cart, {"ube-royale": 1, "happy-camper": 1})

    def test_cash_input_updates_change_and_checkout_without_rebuilding_input(self):
        self.form.open_shop("workstation_specialty_coffee_pos")
        first_product_card = find_component(self.form.root, "product-grid").children[0]
        first_product_card.children[-1].trigger("click")
        cash_input = self.form.cash_input
        cash_input.text = "100"
        cash_input.trigger("change")
        self.assertIs(self.form.cash_input, cash_input)
        self.assertEqual(self.form.change_label.text, "Short by ₱60.00.")
        self.assertFalse(self.form.checkout_button.enabled)

        cash_input.text = "200"
        cash_input.trigger("change")
        self.assertEqual(self.form.change_label.text, "Change due: ₱40.00")
        self.assertTrue(self.form.checkout_button.enabled)
        self.form.checkout_button.trigger("click")
        self.assertEqual(len(tables_store.transactions.rows), 1)
        self.assertFalse(self.form.cart)

    def test_receipt_print_uses_dynamic_javascript_property_lookup(self):
        print_calls = []
        anvil.alert = lambda *args, **kwargs: True
        anvil.js.window.print = lambda: print_calls.append(True)
        self.form.open_shop("workstation_specialty_coffee_pos")
        self.form.show_receipt({
            "timestamp": datetime.now(),
            "items": [],
            "total_amount": 0,
            "payment_method": "Digital",
        })
        self.assertEqual(print_calls, [True])


if __name__ == "__main__":
    unittest.main()
