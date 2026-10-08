import certifi
from pymongo import MongoClient, ASCENDING, DESCENDING
from config import MONGODB_URI, DB_NAME

client = MongoClient(MONGODB_URI, tlsCAFile=certifi.where(), tz_aware=True)
db = client[DB_NAME]

users = db.users                  # customers + admin
company = db.company              # one document: store info and settings
products = db.products            # catalogue, price, stock
carts = db.carts                  # one cart per user
orders = db.orders                # completed orders
payments = db.payments            # payment history
login_history = db.login_history  # signup, login, failed login, logout
activity_log = db.activity_log    # cart add/remove, orders placed, etc.
sessions = db.sessions            # active login tokens (lets logout work)


def create_indexes():
    users.create_index("email", unique=True)
    products.create_index("name", unique=True)
    products.create_index("category")
    carts.create_index("user_id", unique=True)
    orders.create_index("order_number", unique=True)
    orders.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    payments.create_index("user_id")
    login_history.create_index([("created_at", DESCENDING)])
    login_history.create_index("email")
    activity_log.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    sessions.create_index("jti", unique=True)
    sessions.create_index("expire_at", expireAfterSeconds=0)  # auto-delete expired