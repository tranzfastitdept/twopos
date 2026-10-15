# -*- coding: utf-8 -*-
from ._anvil_designer import MainFormTemplate

import anvil
import anvil.js
from anvil import Button, ColumnPanel, FlowPanel, GridPanel, Image, Label, TextBox
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
    picker = ColumnPanel(role="shop-picker-content")
    self.root.add_component(picker)
    picker.add_component(Label(text="TWO STORES · TWO REGISTERS", role="pos-eyebrow"))
    picker.add_component(Label(text="Choose your counter.", role="pos-title"))
    picker.add_component(Label(
      text="Each register has its own menu, checkout, and sales history.",
      role="pos-subtitle",
    ))
    choices = FlowPanel(role="shop-choices")
    picker.add_component(choices)
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
    switch_button = Button(text="←", role="back-link")
    switch_button.set_event_handler("click", lambda **event_args: self.show_shop_picker())
    header.add_component(switch_button)
    header.add_component(Image(
      source=self.current_shop["logo"],
      height=42,
      display_mode="shrink_to_fit",
      role="brand-logo",
    ))
    brand = FlowPanel(role="brand-copy")
    brand.add_component(Label(text=self.current_shop["name"], role="brand-name"))
    brand.add_component(Label(text="POINT OF SALE", role="brand-meta"))
    header.add_component(brand)
    if self.analytics_visible:
      history = Button(text="Back to register  ↗", role="nav-link")
      history.set_event_handler("click", lambda **event_args: self.show_register_view())
    else:
      history = Button(text="Sales & history  ↗", role="nav-link")
      history.set_event_handler("click", lambda **event_args: self.show_analytics())
    header.add_component(history)

    if self.analytics_visible:
      self.render_analytics()
      return

    layout = GridPanel(role="register-layout")
    self.root.add_component(layout)

    menu = ColumnPanel(role="menu-panel")
    layout.add_component(
      menu,
      row="register",
      col_lg=0,
      width_lg=8,
      col_md=0,
      width_md=8,
      col_sm=0,
      width_sm=12,
      col_xs=0,
      width_xs=12,
    )
    section_heading = FlowPanel(role="section-heading")
    heading_copy = FlowPanel(role="section-heading-copy")
    heading_copy.add_component(Label(text="YOUR MENU", role="pos-eyebrow"))
    heading_copy.add_component(Label(text="Good things,\nmade to order.", role="section-title"))
    heading_copy.add_component(Label(
      text="Tap a product card to add it to your basket.",
      role="menu-hint",
    ))
    section_heading.add_component(heading_copy)
    section_heading.add_component(Label(text="{} ITEMS".format(len(self.products)), role="menu-count"))
    menu.add_component(section_heading)
    grid = GridPanel(role="product-grid")
    menu.add_component(grid)
    for index, product in enumerate(self.products):
      card = ColumnPanel(role="product-card")
      card.add_component(Image(
        source=product["image"],
        height=140,
        display_mode="fill_width",
        role="product-image",
      ))
      card.add_component(Label(text=product["name"], role="product-name"))
      card.add_component(Label(text=product["description"], role="product-description"))
      card.add_component(Label(text=self.format_money(product["price"]), role="product-price"))
      card_action = Button(
        text="Add {} to basket".format(product["name"]),
        role="product-card-action",
      )
      card_action.set_event_handler(
        "click",
        lambda product_id=product["product_id"], **event_args: self.change_quantity(product_id, 1),
      )
      card.add_component(card_action)
      grid.add_component(
        card,
        row=str(index // 3),
        col_lg=(index % 3) * 4,
        width_lg=4,
        col_md=(index % 3) * 4,
        width_md=4,
        col_sm=(index % 3) * 4,
        width_sm=4,
        col_xs=0,
        width_xs=12,
      )

    self.basket_panel = ColumnPanel(role="basket-panel")
    layout.add_component(
      self.basket_panel,
      row="register",
      col_lg=8,
      width_lg=4,
      col_md=8,
      width_md=4,
      col_sm=0,
      width_sm=12,
      col_xs=0,
      width_xs=12,
    )
    self.render_basket()

  def change_quantity(self, product_id, change):
    quantity = self.cart.get(product_id, 0) + change
    if quantity <= 0:
      self.cart.pop(product_id, None)
    elif quantity <= 99:
      self.cart[product_id] = quantity
    self.render_basket()

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
    heading = FlowPanel(role="checkout-heading")
    heading_copy = FlowPanel(role="checkout-heading-copy")
    heading_copy.add_component(Label(text="CURRENT ORDER", role="pos-eyebrow"))
    heading_copy.add_component(Label(text="Your basket", role="basket-title"))
    heading.add_component(heading_copy)
    clear_button = Button(text="Clear", role="pos-quiet-button")
    clear_button.set_event_handler("click", lambda **event_args: self.clear_basket())
    heading.add_component(clear_button)
    self.basket_panel.add_component(heading)

    basket_items = ColumnPanel(role="basket-items")
    self.basket_panel.add_component(basket_items)
    total = self.basket_total()
    if not self.cart:
      basket_items.add_component(Label(
        text="Your basket is empty.\nTap an item to get started.",
        role="basket-empty",
      ))
    for product in self.products:
      quantity = self.cart.get(product["product_id"], 0)
      if not quantity:
        continue
      row = FlowPanel(role="basket-row")
      row.add_component(Image(
        source=product["image"],
        height=58,
        display_mode="fill_width",
        role="basket-image",
      ))
      details = ColumnPanel(role="basket-line-info")
      details.add_component(Label(text=product["name"], role="basket-item-name"))
      details.add_component(Label(text="{} each".format(self.format_money(product["price"])), role="basket-unit-price"))
      quantity_control = FlowPanel(role="quantity-control")
      decrease = Button(text="−", role="quantity-button")
      decrease.set_event_handler(
        "click",
        lambda product_id=product["product_id"], **event_args: self.change_quantity(product_id, -1),
      )
      quantity_control.add_component(decrease)
      quantity_control.add_component(Label(text=str(quantity), role="quantity-label"))
      increase = Button(text="+", role="quantity-button")
      increase.set_event_handler(
        "click",
        lambda product_id=product["product_id"], **event_args: self.change_quantity(product_id, 1),
      )
      quantity_control.add_component(increase)
      details.add_component(quantity_control)
      row.add_component(details)
      row.add_component(Label(text=self.format_money(product["price"] * quantity), role="basket-line-total"))
      basket_items.add_component(row)

    checkout_bottom = ColumnPanel(role="checkout-bottom")
    self.basket_panel.add_component(checkout_bottom)
    subtotal = FlowPanel(role="subtotal")
    subtotal.add_component(Label(text="Subtotal", role="subtotal-label"))
    self.basket_total_label = Label(text=self.format_money(total), role="subtotal-value")
    subtotal.add_component(self.basket_total_label)
    checkout_bottom.add_component(subtotal)

    checkout_bottom.add_component(Label(text="Payment method", role="field-label"))
    payment_options = FlowPanel(role="payment-options")
    cash = Button(
      text="Cash",
      role="payment-option-selected" if self.payment_method == "Cash" else "payment-option",
    )
    cash.set_event_handler("click", lambda **event_args: self.set_payment_method("Cash"))
    digital = Button(
      text="Digital",
      role="payment-option-selected" if self.payment_method == "Digital" else "payment-option",
    )
    digital.set_event_handler("click", lambda **event_args: self.set_payment_method("Digital"))
    payment_options.add_component(cash)
    payment_options.add_component(digital)
    checkout_bottom.add_component(payment_options)

    paid = round(self.parse_cash_amount(self.cash_received), 2)
    if self.payment_method == "Cash":
      checkout_bottom.add_component(Label(text="Amount received", role="field-label"))
      cash_input = FlowPanel(role="cash-input-wrap")
      cash_input.add_component(Label(text="₱", role="currency-prefix"))
      self.cash_input = TextBox(
        text=self.cash_received,
        type="number",
        placeholder="0.00",
        role="cash-input",
      )
      self.cash_input.set_event_handler("change", self.cash_input_changed)
      cash_input.add_component(self.cash_input)
      checkout_bottom.add_component(cash_input)
      if paid < total:
        change_text = "Short by {}.".format(self.format_money(total - paid)) if paid else "Enter the amount received."
      else:
        change_text = "Change due: {}".format(self.format_money(paid - total))
      self.change_label = Label(text=change_text, role="change-message")
      checkout_bottom.add_component(self.change_label)
    else:
      self.change_label = None

    checkout_button = FlowPanel(role="checkout-button")
    self.checkout_button = Button(text="Charge", role="charge-action")
    self.checkout_total_label = Label(text=self.format_money(total), role="charge-total")
    checkout_button.add_component(self.checkout_button)
    checkout_button.add_component(self.checkout_total_label)
    self.checkout_button.enabled = bool(self.cart) and (self.payment_method == "Digital" or paid >= total)
    self.checkout_button.set_event_handler("click", self.checkout)
    checkout_bottom.add_component(checkout_button)
    checkout_bottom.add_component(Label(text="Order total is verified at checkout", role="secure-note"))

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
    self.basket_total_label.text = self.format_money(total)
    self.checkout_total_label.text = self.format_money(total)
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
