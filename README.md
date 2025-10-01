# Betta Paradise Shop

Betta Paradise is a Flask-based e-commerce application for selling unique betta fish. It provides a customer-facing storefront, PromptPay and Stripe payments, and a control panel for shop staff.

## Features
- Product browsing with filtering by tail type, colour, grade, and price.
- Localised product descriptions and media galleries.
- Cart and checkout with coupons, shipping quotes, and order tracking.
- PromptPay QR generation, bank transfer slip upload, and Stripe card payments.
- Admin dashboard for order status updates, shipment handling, cancellation workflows, and inventory restock.
- Product management with media uploads and attribute editing.
- Configurable shop profile, payment keys, SEO metadata, and shipping defaults via the admin settings centre.

## Tech Stack
- Python 3.12, Flask 3, SQLAlchemy, Flask-Login, Flask-Babel.
- SQLite default database (configurable via `DATABASE_URL`).
- Stripe SDK, qrcode, Pillow for QR generation and media handling.

## Getting Started
1. **Clone the repository**
   ```bash
   git clone https://github.com/karndiy/pywebbetta.git
   cd pywebbetta
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate            # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Environment variables**
   Copy `.env.example` to `.env` (or export variables) and adjust as needed:
   ```env
   SECRET_KEY=replace-me
   DATABASE_URL=sqlite:///instance/shop.db
   PROMPTPAY_ID=YOUR_PROMPTPAY
   PROMPTPAY_DISPLAY_NAME=Betta Shop
   STRIPE_PUBLIC_KEY=pk_test_xxx
   STRIPE_SECRET_KEY=sk_test_xxx
   SHOP_NAME=Betta Paradise
   SHOP_EMAIL=support@example.com
   SHOP_PHONE=+66-000-0000
   SHOP_ADDRESS=Bangkok, Thailand
   SEO_META_TITLE=Betta Paradise - Unique Betta Fish
   SEO_META_DESCRIPTION=Show grade betta fish for sale.
   ```

5. **Prepare writable directories**
   ```bash
   mkdir -p instance
   mkdir -p betta/static/uploads betta/static/qr
   ```

6. **Initialise the database**
   ```bash
   flask --app app.py shell <<'PY'
from betta.models import init_db
from betta import create_app
app = create_app()
with app.app_context():
    init_db()
PY
   ```

7. **Create an admin user (optional)**
   ```bash
   flask --app app.py create-admin
   ```
   The app also seeds a default admin (`karndiy@gmail.com / admin123`) if none exists.

8. **Run the development server**
   ```bash
   python app.py
   # or
   flask --app app.py run
   ```
   Access the storefront at `http://127.0.0.1:5000/` and admin panel at `http://127.0.0.1:5000/admin/`.

## Deployment Notes
- The project runs well on services such as PythonAnywhere.
- Ensure the `instance/` directory and static upload folders are writable.
- Set production environment variables for secrets and Stripe keys.
- Map `/static/` to `betta/static` when using a WSGI host.

## Project Structure
```
app.py                 # Flask entry point
betta/                 # Application package
  blueprints/          # Store, admin, API blueprints
  services/            # Payments, shipping, media, settings helpers
  templates/           # Jinja templates for store and admin
  static/              # CSS, JS, uploads, generated QR images
  models.py            # SQLAlchemy ORM models and CLI commands
  config.py            # App configuration
requirements.txt       # Python dependencies
.env.example           # Sample environment variables
```

## Known Gaps
- Automated tests are not yet included.
- Stripe webhooks are not configured; admin confirmation handles post-payment reconciliation.

## License
Specify your preferred license here.
