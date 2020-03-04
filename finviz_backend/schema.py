# schema.py
import datetime

from ariadne import QueryType, make_executable_schema, ObjectType
from ariadne.contrib.django.scalars import date_scalar, datetime_scalar
from django.utils import timezone
import requests

type_defs = """
    scalar Date
    scalar DateTime
    
    type Query {
        portfolio: Portfolio!
    }
    
    type Portfolio {
        balance: [Float]!
        openPositions: [Position]!
    }
    
    type Position {
        stock: Stock!
        quantity: Int!
        opened: DateTime!
        closed: DateTime
        price: Float!
    }
    
    type Stock {
        symbol: String!
        name: String!
        latestPrice: Float! 
    }
"""

query = QueryType()
portfolio = ObjectType("Portfolio")
stock = ObjectType("Stock")


@query.field("portfolio")
def resolve_portfolio(*_):
    return dict(open_positions=[])


@portfolio.field("openPositions")
def resolve_open_positions(*_):
    return [{
        "stock": {
            "symbol": "TSLA"
        },
        "quantity": 10,
        "opened": datetime.datetime(2020,1,1,12,0,0),
        "price": 260.95
    },
        {
            "stock": {
                "symbol": "MSFT"
            },
            "quantity": 20,
            "opened": datetime.datetime(2020,1,1,12,0,0),
            "price": 60.95
        }
    ]


@portfolio.field("balance")
def resolve_balance(*_):
    return [100, 200, 300]

@stock.field("latestPrice")
def resolve_latest_price(*_):
    res = requests.get("https://sandbox.iexapis.com/stable/stock/TSLA/quote/?token=Tpk_4445743c028c4933a50a6314a79d2f7d").json()
    return res.get("latestPrice", 0)


schema = make_executable_schema(type_defs, query, portfolio, stock, [date_scalar, datetime_scalar])