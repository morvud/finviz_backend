from django.utils import timezone
from iexfinance import stocks

from portfolio.models import *


def buy_order(clean_input):
    symbol = clean_input.get("symbol")
    quote = stocks.Stock(symbol).get_quote()
    portfolio = Portfolio.objects.first()
    stock, created = Stock.objects.get_or_create(symbol=symbol, name=quote.get("companyName"))
    return Position.objects.create(portfolio=portfolio, stock=stock, quantity=clean_input.get("quantity"),
                                   opened=timezone.now(), price=quote.get("latestPrice"))
