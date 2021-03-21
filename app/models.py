from django.db import models
from djongo.models.fields import ObjectIdField, Field
from django.contrib.auth.models import User


class Profile(models.Model):
    _id = ObjectIdField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # registra gli indirizzi ip dell'utente
    ips = models.Field(default=[])
    # regostra l'email degli utenti che possono compiere operazioni per te
    subprofiles = models.Field(default={})
    # ogni volta che accede si aggiorna la data
    timestamp = models.DateTimeField(auto_now_add=True, auto_now=False)


class Order(models.Model):
    _id = ObjectIdField()
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    buy_sell = models.CharField(max_length=100)
    user_account = models.CharField(max_length=100)
    datetime = models.DateTimeField(auto_now_add=True)
    price = models.FloatField()
    amount = models.FloatField()


class Permission(models.Model):
    STATUS = (
        ('place orders', 'place order'),
        ('post messages', 'post messages'),
        ('all', 'all')
    )
    email = models.Field(blank=True)
    permission = models.CharField(blank=True, max_length=200, null=True, choices=STATUS)
    date_created = models.DateTimeField(auto_now_add=True, null=True)


# è la classe che registra le informazioni dell'utente
class Userpage(models.Model):
    _id = ObjectIdField()
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    name = models.CharField(max_length=200, null=True)
    phone = models.CharField(max_length=200, null=True)
    email = models.CharField(max_length=200, null=True)
    profile_pic = models.ImageField(null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True, null=True)

