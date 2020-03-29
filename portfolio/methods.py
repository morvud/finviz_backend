from django.utils import timezone
from iexfinance import stocks, refdata

from portfolio.models import *


def buy_order(clean_input):
    symbol = clean_input.get("symbol")
    quote = stocks.Stock(symbol).get_quote()
    portfolio = Portfolio.objects.first()
    stock, created = Stock.objects.get_or_create(
        symbol=symbol, name=quote.get("companyName")
    )
    return Position.objects.create(
        portfolio=portfolio,
        stock=stock,
        quantity=clean_input.get("quantity"),
        opened=timezone.now(),
        price=quote.get("latestPrice"),
        long=True,
    )


def sell_order(clean_input):
    symbol = clean_input.get("symbol")
    quote = stocks.Stock(symbol).get_quote()
    portfolio = Portfolio.objects.first()
    stock, created = Stock.objects.get_or_create(
        symbol=symbol, name=quote.get("companyName")
    )
    return Position.objects.create(
        portfolio=portfolio,
        stock=stock,
        quantity=clean_input.get("quantity"),
        opened=timezone.now(),
        price=quote.get("latestPrice"),
        long=False,
    )


def import_stocks():
    items = refdata.get_symbols()
    Stock.objects.bulk_create(
        [Stock(symbol=item.get("symbol"), name=item.get("name")) for item in items]
    )


def sortino(prices, target=0, rfr=0):
    downside_returns = prices.loc[prices < target]
    expected_return = prices.mean()
    down_stdev = downside_returns.std()
    return (expected_return - rfr) / down_stdev
