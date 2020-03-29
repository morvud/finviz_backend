import pandas as pd
from django.db import models
from iexfinance import stocks
from django.utils import timezone
from datetime import datetime, date
from trading_calendars import get_calendar


class Portfolio(models.Model):
    balance = models.FloatField()
    created = models.DateTimeField(auto_now=True)

    def get_balance(self):
        us_calendar = get_calendar("XNYS")
        history = pd.DataFrame(
            [
                {"date": self.created, "amount": self.balance},
                *self.transactions.values("date", "amount"),
                {"date": timezone.now(), "amount": 0},
            ]
        )
        history.set_index("date", inplace=True)
        history = history.resample("d").sum()
        history = history.rename(columns={"amount": "close"})
        history.index = history.index.date
        history["close"] = history.close.cumsum()
        history = history.loc[
            history.apply(lambda x: us_calendar.is_session(x.name), axis=1)
        ]
        return history

    def get_history(self):
        history = self.get_balance()
        for position in self.position_set.all():
            prices = stocks.get_historical_data(
                position.stock.symbol,
                start=position.opened,
                end=position.closed or timezone.now(),
                close_only=True,
                output_format="pandas",
            )
            quote = stocks.Stock(position.stock.symbol).get_quote()
            values = prices.close
            if not position.closed:
                values = values.append(
                    pd.Series(
                        data=quote.get("latestPrice"), index=[datetime.now().date()]
                    )
                )
            q = 1 if position.long else -1
            history["close"] = history["close"].add(
                position.quantity * values.diff().cumsum() * q, fill_value=0,
            )
        return history

    def get_pct_change(self):
        return self.get_history().pct_change()


class Transaction(models.Model):
    amount = models.FloatField()
    date = models.DateTimeField()
    portfolio = models.ForeignKey(
        Portfolio, related_name="transactions", on_delete=models.CASCADE
    )


class Stock(models.Model):
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=255)

    def get_chart(self, start=date(2019, 3, 1), end=datetime.now().date()):
        quote = stocks.Stock(self.symbol).get_quote()
        return stocks.get_historical_data(
            self.symbol, start=start, end=end, close_only=True, output_format="pandas",
        ).close.append(
            pd.Series(data=quote.get("latestPrice"), index=[datetime.now().date()])
        )


class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, null=False)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=False)
    quantity = models.IntegerField()
    opened = models.DateTimeField()
    closed = models.DateTimeField(null=True)
    price = models.FloatField()
    long = models.BooleanField(default=True)
