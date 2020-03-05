# schema.py
import datetime

from ariadne import QueryType, make_executable_schema, ObjectType, MutationType
from ariadne.contrib.django.scalars import date_scalar, datetime_scalar
from graphql import GraphQLResolveInfo
from iexfinance import stocks

from portfolio.methods import buy_order
from portfolio.models import *

type_defs = """
    scalar Date
    scalar DateTime
    
    type Query {
        portfolio: Portfolio!
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
    return buy_order(clean_input)


@portfolio.field("openPositions")
def resolve_open_positions(obj: Portfolio, info: GraphQLResolveInfo):
    return obj.position_set.all()


@portfolio.field("balance")
def resolve_balance(obj: Portfolio, info: GraphQLResolveInfo):
    return obj.balance


@stock.field("latestPrice")
def resolve_latest_price(obj: Stock, info: GraphQLResolveInfo):
    quote = stocks.Stock(obj.symbol).get_quote()
    return quote.get("latestPrice")


schema = make_executable_schema(type_defs, query, mutation, portfolio, stock, [date_scalar, datetime_scalar])
