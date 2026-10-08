from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database as d
from config import CORS_ORIGINS
from routers import auth, products, cart, orders, admin
from utils import ser


@asynccontextmanager
async def lifespan(app: FastAPI):
    d.create_indexes()
    yield


app = FastAPI(title="Fresh Grocery Store API", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS,
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, products.router, cart.router, orders.router, admin.router):
    app.include_router(r)


@app.get("/", tags=["Public"])
def root():
    return {"status": "ok", "app": "Fresh Grocery Store API"}


@app.get("/company", tags=["Public"])
def public_company():
    c = d.company.find_one({}, {"name": 1, "address": 1, "phone": 1, "email": 1,
                                "currency": 1, "delivery_fee": 1, "opening_hours": 1})
    return ser(c) if c else {}