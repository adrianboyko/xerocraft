# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2017-06-07 04:07
from __future__ import unicode_literals

from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_auto_20170606_1616'),
    ]

    operations = [
        migrations.AlterField(
            model_name='consumabletostock',
            name='curr_level',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), help_text='The current inventory level *in the warehouse* (not displayed for sale) ', max_digits=6),
        ),
        migrations.AlterField(
            model_name='consumabletostock',
            name='min_level',
            field=models.DecimalField(decimal_places=2, default=Decimal('0'), help_text='Restock when inventory level *in the warehouse* (not displayed for sale) reaches this low level', max_digits=6),
        ),
    ]
