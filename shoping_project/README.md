# Serein — ladies fashion shop

A Django storefront for women's clothing with a SQLite database, starter collection, category/search filtering, session-based favourites and shopping bag, cash-on-delivery checkout, image uploads, offer pricing, stock tracking, and an order management admin.

## Run locally on Windows

From this folder, activate the existing environment and initialize the database:

```powershell
..\shoping_venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py loaddata starter_collection
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. The custom store dashboard is at `http://127.0.0.1:8000/manage/`; sign in with a Django staff account. Create one with `python manage.py createsuperuser`, or grant an existing account `is_staff` in Django admin. Dashboard, products, inventory, orders, expenses, and settings are all staff protected. The original Django admin remains available at `/admin/`.

The starter collection can be loaded once into an empty database; to reload it, use `python manage.py loaddata starter_collection` after clearing the existing products and categories in admin. Apply new schema changes with `python manage.py migrate` after updating.

SQLite is stored in `db.sqlite3`. In the dashboard, upload a cover image and multiple gallery images, set purchase cost, selling price, sale price, available sizes, and independent stock counts. The legacy product stock field stays synchronized to the sum of size quantities for cart compatibility. Orders reduce stock at checkout and cancellation restores it. Sales and profit reports count delivered orders; new order items store purchase cost when checked out. Historical order items have no purchase cost snapshot and therefore show zero COGS until corrected. Expense records are included in net profit. Favourites and the bag remain stored in each visitor's browser session.
