import pandas as pd
from django.db import models


class Portfolio(models.Model):
    balance = models.FloatField()
    created = models.DateTimeField(auto_now=True)

    def get_history(self):
        df = pd.DataFrame(
            [
                {"date": self.created, "amount": self.balance},
                *self.transactions.values("date", "amount"),
            ]
        )
        df.set_index("date", inplace=True)
        df = df.resample("d").sum()
        df = df.rename(columns={"amount": "close"})
        df.index = df.index.date
        df["close"] = df.close.cumsum()
        return df


class Transaction(models.Model):
    amount = models.FloatField()
    date = models.DateTimeField()
    portfolio = models.ForeignKey(
        Portfolio, related_name="transactions", on_delete=models.CASCADE
    )


class Stock(models.Model):
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=255)


class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, null=False)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=False)
    quantity = models.IntegerField()
    opened = models.DateTimeField()
    closed = models.DateTimeField(null=True)
    price = models.FloatField()
