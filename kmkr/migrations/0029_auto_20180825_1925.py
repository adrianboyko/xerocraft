# Generated by Django 2.1 on 2018-08-26 02:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kmkr', '0028_auto_20180825_1856'),
    ]

    operations = [
        migrations.AlterField(
            model_name='underwritingagreement',
            name='qty_sold',
            field=models.IntegerField(default=1, help_text='.'),
        ),
    ]
