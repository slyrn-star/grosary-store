import database as d
from config import ADMIN_NAME, ADMIN_EMAIL, ADMIN_PASSWORD
from security import hash_password
from utils import now

d.create_indexes()

# Company
if not d.company.find_one({}):
    d.company.insert_one({
        "name": "Fresh Grocery Store", "address": "", "phone": "", "email": "",
        "currency": "INR", "delivery_fee": 0, "opening_hours": "8:00 AM - 10:00 PM",
        "settings": {"cash_on_delivery": True}, "created_at": now()})
    print("Company created")

# Admin account
if not d.users.find_one({"email": ADMIN_EMAIL}):
    d.users.insert_one({"name": ADMIN_NAME, "email": ADMIN_EMAIL,
                        "password_hash": hash_password(ADMIN_PASSWORD),
                        "role": "admin", "is_active": True,
                        "created_at": now(), "last_login_at": None})
    print(f"Admin created: {ADMIN_EMAIL}")

# Products (image names match your frontend; stock is a starting value)
PRODUCTS = [
    ("Apple", "360_F_246698055_Vg3xmiBbRFD3evEsfnHCAXz8lX85nQV9.jpg", 120, "per kg", "Fruits", "🍎"),
    ("Banana", "banana-14586973852378912_l.jpg", 60, "per dozen", "Fruits", "🍌"),
    ("Orange", "images.jpg", 80, "per kg", "Fruits", "🍊"),
    ("Tomato", "Tomato_je.jpg", 40, "per kg", "Vegetables", "🍅"),
    ("Potato", "istockphoto-157430678-612x612.jpg", 35, "per kg", "Vegetables", "🥔"),
    ("Carrot", "istockphoto-1388403435-612x612.jpg", 50, "per kg", "Vegetables", "🥕"),
    ("Milk", "360_F_308503485_OdBhixJbzT3bdC60rghTKU7vRzk1NrDc.jpg", 60, "per litre", "Dairy", "🥛"),
    ("Cheese", "istockphoto-531048911-612x612.jpg", 120, "per pack", "Dairy", "🧀"),
    ("Biscuits", "360_F_224404329_KrZ69DD38fjb4zYKL01AKCy46zALlkWv.jpg", 30, "per packet", "Snacks", "🍪"),
    ("Chips", "360_F_1550681885_0fpGuXJXdI6ZTLRp0GOvZeBc1yj5uNnk.jpg", 40, "per packet", "Snacks", "🍟"),
    ("Juice", "360_F_1389578123_nYTPkMvgBv2NROXZg6TQP5sK8Y42DcDJ.jpg", 90, "per bottle", "Beverages", "🧃"),
    ("Cold Drink", "1-liter-alcohol-free-sweet-and-fizzy-taste-branded-cold-drink-416.jpg", 50, "per bottle", "Beverages", "🥤"),
]

for name, image, price, unit, category, emoji in PRODUCTS:
    d.products.update_one(
        {"name": name},
        {"$setOnInsert": {"name": name, "image": image, "price": price, "unit": unit,
                          "category": category, "emoji": emoji, "stock": 100,
                          "description": "", "is_active": True, "created_at": now(),
                          "updated_at": now()}},
        upsert=True)
print("Products ready. Seeding done.")