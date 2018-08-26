# Generated by Django 2.1 on 2018-08-26 05:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kmkr', '0031_auto_20180825_2249'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='underwritingschedule',
            name='fridays',
        ),
        migrations.RemoveField(
            model_name='underwritingschedule',
            name='mondays',
        ),
        migrations.RemoveField(
            model_name='underwritingschedule',
            name='saturdays',
        ),
        migrations.RemoveField(
            model_name='underwritingschedule',
            name='sundays',
        ),
        migrations.RemoveField(
            model_name='underwritingschedule',
            name='thursdays',
        ),
        migrations.RemoveField(
            model_name='underwritingschedule',
            name='tuesdays',
        ),
        migrations.RemoveField(
            model_name='underwritingschedule',
            name='wednesdays',
        ),
        migrations.AddField(
            model_name='underwritingschedule',
            name='weekdays',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='underwritingschedule',
            name='weekend',
            field=models.BooleanField(default=False),
        ),
    ]
