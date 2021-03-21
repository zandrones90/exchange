from django.db import models
from djongo.models.fields import ObjectIdField, Field
from django.contrib.auth.models import User


class Post(models.Model):
    _id = ObjectIdField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission_user= models.CharField(max_length=100)
    STATUS = (
        (None, None),
        ('BUY', 'BUY'),
        ('SELL', 'SELL'),
    )
    amount = models.FloatField(default='0.00', max_length=200, null=True, blank=True)
    price_per_unit = models.FloatField(default='0.00', max_length=200, null=True, blank=True)
    crypto = models.CharField(max_length=50, default='BTC')
    type_of_transaction = models.CharField(default=None, max_length=4, choices=STATUS, null=True, blank=True)
    content = models.TextField(max_length=200, null=True, blank=True)
    datetime = models.DateTimeField(auto_now_add=True)

