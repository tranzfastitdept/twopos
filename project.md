# TwoPOS: Separate Flask POS Registers

## Project Overview
A web-based point-of-sale system for two small shops. One Flask app serves separate coffee and cookie registers at distinct URLs. Each shop has its own CSV catalog and transaction history.

### Technical Stack
- **Framework**: Flask
- **Language**: Python 3, HTML, CSS, and JavaScript
- **Data storage**: Per-shop CSV files; no SQL database
- **Run locally**: `python -m pip install -r requirements.txt`, then `python app.py`
- **Registers**: `http://127.0.0.1:5000/workstation_specialty_coffee_pos/` and `http://127.0.0.1:5000/keecoo_pos/`
- **Dedicated registers**: Run `start.bat`; Keecoo is on port `51119` and coffee is on port `51120`. Each process is restricted to its own shop. Tunnels can target `http://127.0.0.1:51119` or `http://127.0.0.1:51120`.
- **Chooser**: Running `python app.py` directly keeps the shop selector on port `5000`.

---

## Architecture & Data Models

### 1. Per-shop CSV data

Each shop's files live in its own `data` directory, so menus and transaction records stay separate.

#### `shops.csv`
- `slug`: Register URL and shop folder.
- `name`: Store name shown in the register.
- `logo`: Logo path within that shop's assets.
- `receipt_header`: Closing text on the receipt.

#### `products.csv`
- `id`, `name`, `description`, `price`, and `image` (relative to the shop's `assets` directory).

#### `transactions.csv`
- `txn_id`, `timestamp`, `items_json` (item/quantity/price snapshots), `total_amount`, `payment_method`, `amount_paid`, and `change_given`.

---

## Feature Specifications

### 1. Tenant Selection & Frontend Layout
- The interface will dynamically load configuration profiles based on an initial selector (e.g., switching between "Coffee Shop View" and "Cookie Shop View").
- Clear branding separation using shop names and modular UI banners.

### 2. Frontend Touchscreen Grid (The POS View)
- A responsive, image-heavy grid layout that maps out all records from the `products` table matching the active shop.
- Each tile displays:
  - High-res product thumbnail image.
  - Descriptive item name.
  - Formatted currency price badge.
- **Interactions**: Clicking a product tile instantly increments its quantity inside a sidebar checkout basket.

### 3. Sidebar Basket & Checkout Engine
- Lists current itemizations, individual quantities, price multipliers, and a rolling subtotal sum.
- **Payment Method Toggle**: A binary option selector between **Cash** and **Digital** (e.g., GCash/Maya mockup placeholders).
- **Cash Input Controller**:
  - Visible only when "Cash" payment is chosen.
  - Numeric input field for "Amount Received".
  - **Dynamic Change Calculator**: Computes `Amount Received - Total Price`. Displays a prominent warning if the cash received is insufficient, and locks the checkout submission.

### 4. Back-Office Analytics Dashboard
- A restricted navigation view containing a clean transactional history log.
- Summarizes gross sales figures, volumes categorized by payment types, and table aggregations listing row-by-row historic receipts.

### 5. Receipt Engine
- A dedicated printable popup form component mimicking a standard physical receipt template.
- Programmatically formats the transactional metadata (`items_json`, `timestamp`, and `change_given`) into a clean typography layout optimized for printing (`window.print()`).

---

## Implementation Notes

### Routes and data separation
- `/` selects a register.
- `/<shop-slug>/` serves that shop's point of sale.
- `/<shop-slug>/analytics` shows only that shop's sales and transaction history.
- Product, checkout, analytics, and transaction-receipt JSON endpoints are scoped by the validated shop slug.
- Checkout validates product IDs, prices, quantities, payment method, and received cash on the server; the client never supplies the authoritative total.

### Product assets
Product images and logos remain in each shop's `assets` folder and are referenced by that shop's `products.csv` and `shops.csv`. Original product images are preserved; the catalog points to resized WebP thumbnails in `assets/thumbs` for faster register loading.

### CSV storage note
This local CSV-backed version is intended for a single app process and modest shop traffic. CSV files do not provide database transactions or cross-process write locking; back up each shop's `data` directory when preserving sales history matters.