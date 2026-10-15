# -*- coding: utf-8 -*-
from ._anvil_designer import MainFormTemplate

import anvil
import anvil.js
from anvil import Button, ColumnPanel, FlowPanel, Image, Label, RadioButton, TextBox
import math


class MainForm(MainFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)
    self.cart = {}
    self.products = []
    self.current_shop = None
    self.cash_received = ""
    self.payment_method = "Cash"
    self.analytics_visible = False
    self.root = ColumnPanel(role="pos-shell")
    self.add_component(self.root)
    self.shops = anvil.server.call("get_initial_data")
    self.default_shop = self.shops["default_shop"]
    self.shop_list = self.shops["shops"]
    self.show_shop_picker() if self.default_shop is None else self.open_shop(self.default_shop)

  def reset_form(self):
    self.root.clear()

  def show_shop_picker(self):
    self.current_shop = None
    self.reset_form()
    self.root.add_component(Label(text="TWO STORES · TWO REGISTERS", role="pos-eyebrow"))
    self.root.add_component(Label(text="Choose your counter.", role="pos-title"))
    self.root.add_component(Label(
      text="Each register has its own menu, checkout, and sales history.",
      role="pos-subtitle",
    ))
    choices = FlowPanel(role="shop-choices")
    self.root.add_component(choices)
    for shop in self.shop_list:
      card = ColumnPanel(role="shop-card")
      logo = Image(source=shop["logo"], height=76, display_mode="shrink_to_fit")
      card.add_component(logo)
      card.add_component(Label(text=shop["name"], role="shop-title"))
      open_button = Button(text="Open register  →", role="pos-button")
      open_button.set_event_handler(
        "click",
        lambda slug=shop["slug"], **event_args: self.open_shop(slug),
      )
      card.add_component(open_button)
      choices.add_component(card)

  def open_shop(self, slug):
    self.current_shop = next((shop for shop in self.shop_list if shop["slug"] == slug), None)
    if self.current_shop is None:
      anvil.Notification("That register is unavailable.", style="warning").show()
      self.show_shop_picker()
      return
    self.products = anvil.server.call("get_products_by_shop", slug)
    self.cart = {}
    self.payment_method = "Cash"
    self.cash_received = ""
    self.analytics_visible = False
    self.show_register()

  def show_register(self):
    self.reset_form()
    header = FlowPanel(role="pos-header")
    self.root.add_component(header)
    if self.default_shop is None:
      switch_button = Button(text="← Shops", role="pos-quiet-button")
      switch_button.set_event_handler("click", lambda **event_args: self.show_shop_picker())
      header.add_component(switch_button)
    header.add_component(Image(source=self.current_shop["logo"], height=44, display_mode="shrink_to_fit"))
    header.add_component(Label(text=self.current_shop["name"], role="pos-brand"))
    if self.analytics_visible:
      history = Button(text="← Register", role="pos-quiet-button")
      history.set_event_handler("click", lambda **event_args: self.show_register_view())
    else:
      history = Button(text="Sales & history", role="pos-quiet-button")
      history.set_event_handler("click", lambda **event_args: self.show_analytics())
    header.add_component(history)

    if self.analytics_visible:
      self.render_analytics()
      return

    self.root.add_component(Label(text="YOUR MENU", role="pos-eyebrow"))
    self.root.add_component(Label(text="Good things, made to order.", role="pos-title"))
    layout = FlowPanel(role="register-layout")
    self.root.add_component(layout)

    menu = ColumnPanel(role="menu-panel")
    layout.add_component(menu)
    grid = FlowPanel(role="product-grid")
    menu.add_component(grid)
    for product in self.products:
      card = ColumnPanel(role="product-card")
      card.add_component(Image(source=product["image"], height=190, display_mode="fill_width"))
      card.add_component(Label(text=product["name"], role="product-name"))
      card.add_component(Label(text=product["description"], role="product-description"))
      card.add_component(Label(text=self.format_money(product["price"]), role="product-price"))
      add_button = Button(text="Add to basket  +", role="pos-button")
      add_button.set_event_handler(
        "click",
        lambda product_id=product["product_id"], **event_args: self.change_quantity(product_id, 1),
      )
      card.add_component(add_button)
      grid.add_component(card)

    self.basket_panel = ColumnPanel(role="basket-panel")
    layout.add_component(self.basket_panel)
    self.render_basket()

  def change_quantity(self, product_id, change):
    quantity = self.cart.get(product_id, 0) + change
    if quantity <= 0:
      self.cart.pop(product_id, None)
    elif quantity <= 99:
      self.cart[product_id] = quantity
    self.render_register()

  def render_register(self):
    self.show_register()

  def basket_total(self):
    prices = {product["product_id"]: product["price"] for product in self.products}
    return round(sum(prices[item_id] * quantity for item_id, quantity in self.cart.items()), 2)

  @staticmethod
  def parse_cash_amount(value):
    text = str(value or "").strip()
    if not text or text == "." or text.count(".") > 1:
      return 0
    if not all(character in "0123456789." for character in text):
      return 0
    amount = float(text)
    return amount if not math.isnan(amount) and not math.isinf(amount) else 0

  def render_basket(self):
    self.basket_panel.clear()
    heading = FlowPanel(role="basket-heading")
    heading.add_component(Label(text="Your basket", role="basket-title"))
    clear_button = Button(text="Clear", role="pos-quiet-button")
    clear_button.set_event_handler("click", lambda **event_args: self.clear_basket())
    heading.add_component(clear_button)
    self.basket_panel.add_component(heading)

    total = self.basket_total()
    if not self.cart:
      self.basket_panel.add_component(Label(
        text="Your basket is empty. Tap an item to get started.",
        role="basket-empty",
      ))
    for product in self.products:
      quantity = self.cart.get(product["product_id"], 0)
      if not quantity:
        continue
      row = FlowPanel(role="basket-row")
      row.add_component(Label(
        text="{} × {}".format(quantity, product["name"]),
        role="basket-item-name",
      ))
      row.add_component(Label(text=self.format_money(product["price"] * quantity), role="basket-line-total"))
      decrease = Button(text="−", role="quantity-button")
      decrease.set_event_handler(
        "click",
        lambda product_id=product["product_id"], **event_args: self.change_quantity(product_id, -1),
      )
      row.add_component(decrease)
      row.add_component(Label(text=str(quantity), role="quantity-label"))
      increase = Button(text="+", role="quantity-button")
      increase.set_event_handler(
        "click",
        lambda product_id=product["product_id"], **event_args: self.change_quantity(product_id, 1),
      )
      row.add_component(increase)
      self.basket_panel.add_component(row)

    self.basket_total_label = Label(
      text="Subtotal   {}".format(self.format_money(total)),
      role="basket-total",
    )
    self.basket_panel.add_component(self.basket_total_label)
    payment_options = FlowPanel(role="payment-options")
    cash = RadioButton(text="Cash", group_name="payment-method", selected=self.payment_method == "Cash")
    cash.set_event_handler("change", lambda **event_args: self.set_payment_method("Cash"))
    digital = RadioButton(text="Digital", group_name="payment-method", selected=self.payment_method == "Digital")
    digital.set_event_handler("change", lambda **event_args: self.set_payment_method("Digital"))
    payment_options.add_component(cash)
    payment_options.add_component(digital)
    self.basket_panel.add_component(Label(text="Payment method", role="field-label"))
    self.basket_panel.add_component(payment_options)

    if self.payment_method == "Cash":
      self.basket_panel.add_component(Label(text="Amount received", role="field-label"))
      self.cash_input = TextBox(
        text=self.cash_received,
        type="number",
        placeholder="0.00",
        role="cash-input",
      )
      self.cash_input.set_event_handler("change", self.cash_input_changed)
      self.basket_panel.add_component(self.cash_input)
      paid = round(self.parse_cash_amount(self.cash_received), 2)
      if paid < total:
        change_text = "Short by {}.".format(self.format_money(total - paid)) if paid else "Enter the amount received."
      else:
        change_text = "Change due: {}".format(self.format_money(paid - total))
      self.change_label = Label(text=change_text, role="change-message")
      self.basket_panel.add_component(self.change_label)
    else:
      self.change_label = None

    self.checkout_button = Button(
      text="Charge {}".format(self.format_money(total)),
      role="pos-button",
    )
    self.checkout_button.enabled = bool(self.cart) and (self.payment_method == "Digital" or paid >= total)
    self.checkout_button.set_event_handler("click", self.checkout)
    self.basket_panel.add_component(self.checkout_button)

  def clear_basket(self):
    self.cart = {}
    self.cash_received = ""
    self.render_register()

  def set_payment_method(self, method):
    self.payment_method = method
    self.render_register()

  def cash_input_changed(self, **event_args):
    self.cash_received = self.cash_input.text or ""
    self.update_checkout_state()

  def update_checkout_state(self):
    total = self.basket_total()
    self.basket_total_label.text = "Subtotal   {}".format(self.format_money(total))
    self.checkout_button.text = "Charge {}".format(self.format_money(total))
    paid = round(self.parse_cash_amount(self.cash_received), 2)
    if self.change_label is not None:
      if paid <= 0:
        self.change_label.text = "Enter the amount received."
      elif paid < total:
        self.change_label.text = "Short by {}.".format(self.format_money(total - paid))
      else:
        self.change_label.text = "Change due: {}".format(self.format_money(paid - total))
    self.checkout_button.enabled = bool(self.cart) and (
      self.payment_method == "Digital" or paid >= total
    )

  def checkout(self, **event_args):
    order = anvil.server.call(
      "submit_transaction",
      self.current_shop["slug"],
      [{"product_id": key, "quantity": value} for key, value in self.cart.items()],
      self.payment_method,
      self.cash_received,
    )
    self.cart = {}
    self.cash_received = ""
    self.render_register()
    self.show_receipt(order)

  def show_analytics(self):
    self.analytics_visible = True
    self.show_register()

  def show_register_view(self):
    self.analytics_visible = False
    self.show_register()

  def render_analytics(self):
    data = anvil.server.call("get_shop_analytics", self.current_shop["slug"])
    summary = FlowPanel(role="analytics-summary")
    self.root.add_component(summary)
    for title, value in (
      ("Gross sales", data["gross_sales"]),
      ("Orders", str(data["order_count"])),
      ("Cash sales", data["cash_sales"]),
      ("Digital sales", data["digital_sales"]),
    ):
      card = ColumnPanel(role="metric-card")
      card.add_component(Label(text=title, role="field-label"))
      card.add_component(Label(text=value, role="metric-value"))
      summary.add_component(card)
    self.root.add_component(Label(text="Recent transactions", role="basket-title"))
    for order in data["transactions"]:
      names = ", ".join(
        "{} × {}".format(item["quantity"], item["name"])
        for item in order["items"]
      )
      row = FlowPanel(role="history-row")
      details = Label(
        text="{} · {} · {}".format(
          names,
          order["timestamp"].strftime("%Y-%m-%d %H:%M"),
          order["payment_method"],
        ),
        role="history-detail",
      )
      row.add_component(details)
      row.add_component(Label(text=self.format_money(order["total_amount"]), role="basket-line-total"))
      receipt_button = Button(text="Receipt", role="pos-quiet-button")
      receipt_button.set_event_handler(
        "click",
        lambda receipt=order, **event_args: self.show_receipt(receipt),
      )
      row.add_component(receipt_button)
      self.root.add_component(row)
    if not data["transactions"]:
      self.root.add_component(Label(text="No completed orders yet.", role="basket-empty"))

  def show_receipt(self, order):
    receipt = ColumnPanel(role="receipt")
    receipt.add_component(Label(text="CUSTOMER RECEIPT", role="pos-eyebrow"))
    receipt.add_component(Label(text=self.current_shop["name"], role="receipt-title"))
    receipt.add_component(Label(
      text=order["timestamp"].strftime("%Y-%m-%d %H:%M"),
      role="history-detail",
    ))
    for item in order["items"]:
      receipt.add_component(Label(
        text="{} × {}   {}".format(
          item["quantity"],
          item["name"],
          self.format_money(item["line_total"]),
        ),
        role="receipt-line",
      ))
    receipt.add_component(Label(
      text="TOTAL   {}".format(self.format_money(order["total_amount"])),
      role="receipt-total",
    ))
    receipt.add_component(Label(
      text="Payment: {}".format(order["payment_method"]),
      role="receipt-line",
    ))
    if order["payment_method"] == "Cash":
      receipt.add_component(Label(
        text="Paid: {}".format(self.format_money(order["amount_paid"])),
        role="receipt-line",
      ))
      receipt.add_component(Label(
        text="Change: {}".format(self.format_money(order["change_given"])),
        role="receipt-line",
      ))
    receipt.add_component(Label(text=self.current_shop["receipt_header"], role="receipt-footer"))
    result = anvil.alert(
      receipt,
      title="Customer receipt",
      buttons=[("Close", False), ("Print", True)],
      large=True,
    )
    if result:
      getattr(anvil.js.window, "print")()

  @staticmethod
  def format_money(value):
    return "₱{:,.2f}".format(float(value))
