from django.db import models


class Portfolio(models.Model):
    balance = models.FloatField()


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
