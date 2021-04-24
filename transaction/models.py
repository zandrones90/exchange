from django.db import models
from djongo.models.fields import ObjectIdField, Field
from django.contrib.auth.models import User


class Post(models.Model):
    _id = ObjectIdField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account= models.CharField(max_length=100)
    STATUS = (
        ('BUY', 'BUY'),
        ('SELL', 'SELL'),
    )
    amount = models.FloatField(default='0.00', null=True, blank=True)
    price = models.FloatField(default='0.00', null=True, blank=True)
    type_of_transaction = models.CharField(default=None, max_length=4, choices=STATUS, null=True, blank=True)
    datetime = models.DateTimeField(auto_now_add=True)

