(() => {
  const page = document.body;
  const slug = page.dataset.shop;
  const money = (value) => `₱${Number(value).toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  function showReceipt(order) {
    const overlay = document.getElementById("receipt-overlay");
    const article = document.createElement("article");
    article.className = "receipt";
    article.innerHTML = `
      <button class="receipt-close no-print" type="button" aria-label="Close receipt">×</button>
      <p class="receipt-kicker">CUSTOMER RECEIPT</p><h2></h2><p class="receipt-date"></p><hr>
      <div class="receipt-items"></div><hr><div class="receipt-total"><span>Total</span><strong></strong></div>
      <p class="receipt-payment"></p><p class="receipt-footer"></p>
      <div class="receipt-actions no-print"><button class="secondary-button" type="button">Close</button><button class="checkout-button print-button" type="button">Print receipt</button></div>`;
    article.querySelector("h2").textContent = page.dataset.name;
    article.querySelector(".receipt-date").textContent = new Date(order.timestamp).toLocaleString();
    for (const item of order.items) {
      const row = document.createElement("div");
      row.className = "receipt-item";
      row.innerHTML = "<span></span><strong></strong>";
      row.children[0].textContent = `${item.quantity} × ${item.name}`;
      row.children[1].textContent = money(item.line_total);
      article.querySelector(".receipt-items").append(row);
    }
    article.querySelector(".receipt-total strong").textContent = money(order.total_amount);
    article.querySelector(".receipt-payment").textContent = order.payment_method === "Cash"
      ? `Cash · Paid ${money(order.amount_paid)} · Change ${money(order.change_given)}`
      : "Digital payment";
    article.querySelector(".receipt-footer").textContent = page.dataset.receiptHeader;
    overlay.replaceChildren(article);
    overlay.hidden = false;
    article.querySelectorAll(".receipt-close, .secondary-button").forEach((button) => button.addEventListener("click", () => { overlay.hidden = true; }));
    article.querySelector(".print-button").addEventListener("click", () => window.print());
  }

  async function loadAnalytics() {
    const response = await fetch(`/${slug}/api/analytics`);
    if (!response.ok) throw new Error("Could not load sales history.");
    const data = await response.json();
    document.getElementById("gross-sales").textContent = money(data.gross_sales);
    document.getElementById("order-count").textContent = data.order_count.toLocaleString();
    document.getElementById("cash-sales").textContent = money(data.cash_sales);
    document.getElementById("digital-sales").textContent = money(data.digital_sales);
    document.getElementById("history-count").textContent = `${data.transactions.length} ORDERS`;
    const list = document.getElementById("transactions-list");
    if (!data.transactions.length) {
      list.innerHTML = '<p class="empty-history">No orders yet. Completed checkouts will appear here.</p>';
      return;
    }
    for (const order of data.transactions) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "transaction-row";
      const info = document.createElement("span");
      info.className = "transaction-info";
      const name = document.createElement("strong");
      name.textContent = order.items.map((item) => `${item.quantity} × ${item.name}`).join(", ");
      const meta = document.createElement("small");
      meta.textContent = `${new Date(order.timestamp).toLocaleString()} · ${order.payment_method}`;
      info.append(name, meta);
      const total = document.createElement("strong");
      total.className = "transaction-total";
      total.textContent = money(order.total_amount);
      button.append(info, total);
      button.addEventListener("click", () => showReceipt(order));
      list.append(button);
    }
  }

  loadAnalytics().catch((error) => {
    document.getElementById("transactions-list").textContent = error.message;
  });
})();
