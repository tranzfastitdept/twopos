(() => {
  const page = document.body;
  const slug = page.dataset.shop;
  const cart = new Map();
  let products = [];

  const formatMoney = (cents) => `₱${(cents / 100).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  const asCents = (value) => {
    const amount = Number(value);
    return Number.isFinite(amount) ? Math.round(amount * 100) : 0;
  };
  const totalCents = () => [...cart].reduce((sum, [id, quantity]) => {
    const product = products.find((item) => item.id === id);
    return sum + (product ? asCents(product.price) * quantity : 0);
  }, 0);
  const method = () => document.querySelector('input[name="payment-method"]:checked').value;

  function renderBasket() {
    const container = document.getElementById("basket-items");
    const entries = [...cart].map(([id, quantity]) => ({ product: products.find((item) => item.id === id), quantity })).filter((entry) => entry.product);
    container.replaceChildren();
    document.getElementById("basket-empty").hidden = entries.length > 0;
    for (const { product, quantity } of entries) {
      const line = document.createElement("article");
      line.className = "basket-line";
      line.innerHTML = `
        <img src="/assets/${slug}/${product.image}" alt="">
        <div class="basket-line-info"><strong></strong><span></span><div class="quantity-control"><button type="button" aria-label="Remove one">−</button><span>${quantity}</span><button type="button" aria-label="Add one">+</button></div></div>
        <strong class="line-total">${formatMoney(asCents(product.price) * quantity)}</strong>`;
      line.querySelector(".basket-line-info strong").textContent = product.name;
      line.querySelector(".basket-line-info > span").textContent = `${formatMoney(asCents(product.price))} each`;
      const buttons = line.querySelectorAll(".quantity-control button");
      buttons[0].addEventListener("click", () => adjust(product.id, -1));
      buttons[1].addEventListener("click", () => adjust(product.id, 1));
      container.append(line);
    }
    const total = totalCents();
    document.getElementById("basket-total").textContent = formatMoney(total);
    document.getElementById("button-total").textContent = formatMoney(total);
    updatePayment();
  }

  function adjust(id, change) {
    const next = (cart.get(id) || 0) + change;
    if (next <= 0) cart.delete(id);
    else if (next <= 99) cart.set(id, next);
    renderBasket();
  }

  function updatePayment() {
    const isCash = method() === "Cash";
    document.getElementById("cash-panel").hidden = !isCash;
    const received = asCents(document.getElementById("cash-received").value);
    const total = totalCents();
    const enough = !isCash || (received >= total && total > 0);
    const button = document.getElementById("checkout-button");
    button.disabled = total <= 0 || !enough;
    const message = document.getElementById("change-message");
    message.classList.remove("is-error", "is-success");
    if (!isCash) message.textContent = "";
    else if (total <= 0) message.textContent = "Add products to begin checkout.";
    else if (received <= 0) message.textContent = "Enter the amount received.";
    else if (received < total) {
      message.textContent = `Short by ${formatMoney(total - received)}.`;
      message.classList.add("is-error");
    } else {
      message.textContent = `Change due: ${formatMoney(received - total)}`;
      message.classList.add("is-success");
    }
  }

  function showReceipt(order) {
    const overlay = document.getElementById("receipt-overlay");
    const article = document.createElement("article");
    article.className = "receipt";
    article.innerHTML = `
      <button class="receipt-close no-print" type="button" aria-label="Close receipt">×</button>
      <p class="receipt-kicker">CUSTOMER RECEIPT</p>
      <h2></h2><p class="receipt-date"></p><hr>
      <div class="receipt-items"></div><hr>
      <div class="receipt-total"><span>Total</span><strong></strong></div>
      <p class="receipt-payment"></p><p class="receipt-footer"></p>
      <div class="receipt-actions no-print"><button class="secondary-button" type="button">Done</button><button class="checkout-button print-button" type="button">Print receipt</button></div>`;
    article.querySelector("h2").textContent = page.dataset.name;
    article.querySelector(".receipt-date").textContent = new Date(order.timestamp).toLocaleString();
    for (const item of order.items) {
      const row = document.createElement("div");
      row.className = "receipt-item";
      row.innerHTML = `<span></span><strong></strong>`;
      row.children[0].textContent = `${item.quantity} × ${item.name}`;
      row.children[1].textContent = formatMoney(asCents(item.line_total));
      article.querySelector(".receipt-items").append(row);
    }
    article.querySelector(".receipt-total strong").textContent = formatMoney(asCents(order.total_amount));
    article.querySelector(".receipt-payment").textContent = order.payment_method === "Cash"
      ? `Cash · Paid ${formatMoney(asCents(order.amount_paid))} · Change ${formatMoney(asCents(order.change_given))}`
      : "Digital payment";
    article.querySelector(".receipt-footer").textContent = page.dataset.receiptHeader;
    overlay.replaceChildren(article);
    overlay.hidden = false;
    article.querySelectorAll(".receipt-close, .secondary-button").forEach((button) => button.addEventListener("click", () => { overlay.hidden = true; }));
    article.querySelector(".print-button").addEventListener("click", () => window.print());
  }

  async function loadProducts() {
    const response = await fetch(`/${slug}/api/products`);
    if (!response.ok) throw new Error("Could not load this shop's menu.");
    products = await response.json();
    document.getElementById("product-count").textContent = `${products.length} ITEMS`;
    const grid = document.getElementById("catalog-grid");
    for (const product of products) {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "product-card";
      card.innerHTML = `<span class="product-image"><img alt=""></span><span class="product-details"><strong></strong><span class="product-description"></span><span class="product-price"></span></span><span class="add-mark" aria-hidden="true">+</span>`;
      card.querySelector("img").src = `/assets/${slug}/${product.image}`;
      card.querySelector("img").alt = product.name;
      card.querySelector(".product-details strong").textContent = product.name;
      card.querySelector(".product-description").textContent = product.description;
      card.querySelector(".product-price").textContent = formatMoney(asCents(product.price));
      card.addEventListener("click", () => adjust(product.id, 1));
      grid.append(card);
    }
    renderBasket();
  }

  document.querySelectorAll('input[name="payment-method"]').forEach((input) => input.addEventListener("change", updatePayment));
  document.getElementById("cash-received").addEventListener("input", updatePayment);
  document.getElementById("clear-basket").addEventListener("click", () => { cart.clear(); renderBasket(); });
  document.getElementById("checkout-button").addEventListener("click", async () => {
    const button = document.getElementById("checkout-button");
    const error = document.getElementById("checkout-error");
    error.textContent = "";
    button.disabled = true;
    try {
      const response = await fetch(`/${slug}/api/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          items: [...cart].map(([product_id, quantity]) => ({ product_id, quantity })),
          payment_method: method(),
          amount_paid: document.getElementById("cash-received").value,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error || "Checkout failed. Please try again.");
      cart.clear();
      document.getElementById("cash-received").value = "";
      renderBasket();
      showReceipt(result);
    } catch (failure) {
      error.textContent = failure.message;
      updatePayment();
    }
  });

  loadProducts().catch((error) => {
    document.getElementById("catalog-grid").innerHTML = `<p class="error-message"></p>`;
    document.querySelector("#catalog-grid .error-message").textContent = error.message;
  });
})();
