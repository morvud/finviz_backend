# schema.py
import datetime

import pandas as pd
from ariadne import QueryType, make_executable_schema, ObjectType, MutationType
from ariadne.contrib.django.scalars import date_scalar, datetime_scalar
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from graphql import GraphQLResolveInfo
from iexfinance import stocks, utils
import numpy as np

from portfolio.methods import buy_order
from portfolio.models import *

type_defs = """
    scalar Date
    scalar DateTime
    
    type Query {
        portfolio: Portfolio!
        stock(symbol: String!): Stock
        stocks(symbol: String): [Stock]!
    }
    
    type Mutation {
        buy(input: BuyInput!): BuyPayload
    }
    
    input BuyInput {
        symbol: String!
        quantity: Int!
    }
    
    type BuyPayload {
        stock: Stock!
        quantity: Int!
        price: Float!
    }
    
    type Portfolio {
        balance: [Float]!
        history: [[Float]]!
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
mutation = MutationType()
portfolio = ObjectType("Portfolio")
stock = ObjectType("Stock")


@query.field("portfolio")
def resolve_portfolio(*_):
    return Portfolio.objects.first()


@mutation.field("buy")
def resolve_buy(_, info: GraphQLResolveInfo, input):
    clean_input = {
        "symbol": input.get("symbol"),
        "quantity": input.get("quantity"),
    }
    position = buy_order(clean_input)
    p = Portfolio.objects.first()
    Transaction.objects.create(
        amount=-position.quantity * position.price, portfolio=p, date=position.opened
    )
    return position


@query.field("stock")
def resolve_stock(_, info: GraphQLResolveInfo, symbol: str):
    return Stock.objects.get(symbol=symbol)


@query.field("stocks")
def resolve_stocks(_, info: GraphQLResolveInfo, symbol: str):
    if symbol:
        return Stock.objects.filter(symbol__icontains=symbol)[:10]
    return Stock.objects.all()[:10]


@portfolio.field("openPositions")
def resolve_open_positions(obj: Portfolio, info: GraphQLResolveInfo):
    res = {}
    for position in obj.position_set.filter(closed=None).order_by("opened"):
        if res.get(position.stock.symbol):
            res[position.stock.symbol].quantity += position.quantity
        else:
            res[position.stock.symbol] = position
    return res.values()


@portfolio.field("balance")
def resolve_balance(obj: Portfolio, info: GraphQLResolveInfo):
    return obj.balance


@portfolio.field("history")
def resolve_history(obj: Portfolio, info: GraphQLResolveInfo):
    positions = obj.position_set.all()
    history = obj.get_history()
    print(history)
    for position in positions:
        prices = stocks.get_historical_data(
            position.stock.symbol,
            start=position.opened,
            end=position.closed or timezone.now(),
            close_only=True,
            output_format="pandas",
        )
        values = prices.close
        history["close"] = history["close"].add(
            position.quantity * values, fill_value=0
        )
    return list(
        zip([1000 * x.timestamp() for x in history.index], history.close.values)
    )


@stock.field("latestPrice")
def resolve_latest_price(obj: Stock, info: GraphQLResolveInfo):
    quote = stocks.Stock(obj.symbol).get_quote()
    return quote.get("latestPrice")


schema = make_executable_schema(
    type_defs, query, mutation, portfolio, stock, [date_scalar, datetime_scalar]
)
