# TwoPOS: Flask POS Registers and Anvil Deployment

## Project Overview
A web-based point-of-sale system for two small shops. The same repository supports a local Flask version with per-shop CSV storage and a native Anvil version using Anvil Data Tables.

### Technical Stack
- **Framework**: Flask
- **Language**: Python 3, HTML, CSS, and JavaScript
- **Local Flask data storage**: Per-shop CSV files
- **Anvil hosted data storage**: Anvil Data Tables, seeded automatically from the shop catalog in `server_code/catalog.py`
- **Run locally**: `python -m pip install -r requirements.txt`, then `python app.py`
- **Registers**: `http://127.0.0.1:5000/workstation_specialty_coffee_pos/` and `http://127.0.0.1:5000/keecoo_pos/`
- **Dedicated registers**: Run `start.bat`; Keecoo is on port `51119` and coffee is on port `51120`. Each process is restricted to its own shop. Tunnels can target `http://127.0.0.1:51119` or `http://127.0.0.1:51120`.
- **Chooser**: Running `python app.py` directly keeps the shop selector on port `5000`.

## Anvil.works deployment

The repository root is also a Git-cloneable Anvil app (`anvil.yaml`, `client_code`, `server_code`, and `theme`). In Anvil's Start Page, select **Clone from GitHub** and clone this repository's root. The app schema defines the `shops`, `products`, and `transactions` Data Tables. On its first launch, a server transaction seeds both menus. Each cloned Anvil app has its own database and sales history; Anvil deployments do not write the workstation's CSV transaction files.

To create two dedicated Anvil registers, clone the same repository into **two Anvil apps**. On first launch each app creates a blank `default_shop` row in the `app_settings` Data Table. In each app's Data Tables editor, set that row's `value`:

- Keecoo app: `keecoo_pos`
- Coffee app: `workstation_specialty_coffee_pos`

Each app then opens directly into its configured register and its server rejects calls for the other shop. Leave the value blank to keep the shop chooser. Publish each dedicated Anvil app separately to get a distinct hosted URL. The source is shared in Git while each app's Data Tables (including its register setting) are independent. For private GitHub repositories, check Anvil's current plan requirements for GitHub integration.

---

## Architecture & Data Models

### 1. Per-shop CSV data (Flask)

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

### Anvil database note
The Anvil app is a separate hosted implementation of the same POS workflow. It stores products and sales in Anvil Data Tables, seeds the two menus on first load, and stores product thumbnails as app assets. Changes to the CSV menus should also be reflected in `server_code/catalog.py` before pushing an Anvil update.