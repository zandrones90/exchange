# Generated by Django 3.0.5 on 2021-04-18 20:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='btcwallet',
            name='price',
            field=models.FloatField(),
        ),
        migrations.AlterField(
            model_name='btcwallet',
            name='wallet',
            field=models.FloatField(),
        ),
    ]