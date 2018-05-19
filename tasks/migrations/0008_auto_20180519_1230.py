# Generated by Django 2.0.3 on 2018-05-19 19:30

import abutils.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0019_auto_20180422_1221'),
        ('tasks', '0007_remove_worker_last_work_mtd_reported'),
    ]

    operations = [
        migrations.CreateModel(
            name='Play',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('play_date', models.DateField(help_text='The date on which the member played.')),
                ('play_start_time', models.TimeField(blank=True, help_text='The time at which play began.', null=True)),
                ('play_duration', models.DurationField(blank=True, help_text='Time spent playing. Only blank if play is in progress or member forgot to check out.', null=True, validators=[abutils.validators.positive_duration])),
                ('playing_member', models.ForeignKey(help_text='The member who played.', on_delete=django.db.models.deletion.PROTECT, to='members.Member')),
            ],
        ),
        migrations.RemoveField(
            model_name='timeaccountentry',
            name='expiration',
        ),
        migrations.RemoveField(
            model_name='timeaccountentry',
            name='play',
        ),
        migrations.RemoveField(
            model_name='timeaccountentry',
            name='work',
        ),
        migrations.RemoveField(
            model_name='timeaccountentry',
            name='worker',
        ),
        migrations.DeleteModel(
            name='TimeAccountEntry',
        ),
    ]
