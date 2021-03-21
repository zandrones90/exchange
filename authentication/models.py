from django.db import models
from djongo.models.fields import ObjectIdField, Field
from django.contrib.auth.models import User

class BtcWallet(models.Model):
    _id = ObjectIdField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    wallet = models.FloatField( max_length= 100)
    unit_price = models.FloatField( max_length= 100)
    crypto = models.CharField(max_length=50, default='BTC')
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)


