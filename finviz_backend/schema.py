# schema.py
from datetime import datetime

import pandas as pd
from ariadne import QueryType, make_executable_schema, ObjectType, MutationType
from ariadne.contrib.django.scalars import date_scalar, datetime_scalar
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from graphql import GraphQLResolveInfo
from iexfinance import stocks, utils
import numpy as np

from portfolio.methods import buy_order, sell_order
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
        buy(input: TransactionInput!): TransactionPayload
        sell(input: TransactionInput!): TransactionPayload
    }
    
    input TransactionInput {
        symbol: String!
        quantity: Int!
    }
    
    type TransactionPayload {
        stock: Stock!
        quantity: Int!
        price: Float!
    }
    
    type Portfolio {
        balance: Float!
        history: [[Float]]!
        change: [[Float]]!
        openPositions: [Position]!
        sectors: [Sector]!
        sortino: Float!
    }
    
    type Sector {
        name: String!
        share: Float!
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
        chart: [[Float]]!
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
    return position


@mutation.field("sell")
def resolve_sell(_, info: GraphQLResolveInfo, input):
    clean_input = {
        "symbol": input.get("symbol"),
        "quantity": input.get("quantity"),
    }
    position = sell_order(clean_input)
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
    return obj.get_balance().close.values[-1]


@portfolio.field("sortino")
def resolve_sortino(obj: Portfolio, info: GraphQLResolveInfo):
    positions = obj.position_set.order_by("opened")
    df = stocks.get_historical_data(
        list(positions.values_list("stock__symbol", flat=True)),
        start=positions.first().opened,
        end=timezone.now(),
        output_format="pandas",
        close_only=True,
    )

    return 0


@portfolio.field("sectors")
def resolve_sectors(obj: Portfolio, info: GraphQLResolveInfo):
    positions = obj.position_set.all()
    sectors = []
    for position in positions:
        sectors.append(
            {
                "name": stocks.Stock(position.stock.symbol).get_sector(),
                "share": position.quantity * position.price,
            }
        )
    total = sum([sector.get("share") for sector in sectors])
    sectors = [{**sector, "share": sector.get("share") / total} for sector in sectors]
    return sectors


@portfolio.field("history")
def resolve_history(obj: Portfolio, info: GraphQLResolveInfo):
    history = obj.get_history()
    return list(
        zip(
            [
                1000 * datetime.timestamp(datetime.combine(x, datetime.min.time()))
                for x in history.index
            ],
            history.close.values,
        )
    )


@portfolio.field("change")
def resolve_change(obj: Portfolio, info: GraphQLResolveInfo):
    history = obj.get_pct_change()
    return list(
        zip(
            [
                1000 * datetime.timestamp(datetime.combine(x, datetime.min.time()))
                for x in history.index
            ],
            100 * history.close.fillna(0).values,
        )
    )


@stock.field("latestPrice")
def resolve_latest_price(obj: Stock, info: GraphQLResolveInfo):
    quote = stocks.Stock(obj.symbol).get_quote()
    return quote.get("latestPrice")


@stock.field("chart")
def resolve_chart(obj: Stock, info: GraphQLResolveInfo):
    chart = obj.get_chart()
    return list(
        zip(
            [
                1000 * datetime.timestamp(datetime.combine(x, datetime.min.time()))
                for x in chart.index
            ],
            chart.values,
        )
    )


schema = make_executable_schema(
    type_defs, query, mutation, portfolio, stock, [date_scalar, datetime_scalar]
)
