from django.db import models
from djongo.models.fields import ObjectIdField, Field
from django.contrib.auth.models import User

class BtcWallet(models.Model):
    _id = ObjectIdField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    wallet = models.FloatField()
    price = models.FloatField()
    updated = models.DateTimeField(auto_now_add=False, auto_now=True)


