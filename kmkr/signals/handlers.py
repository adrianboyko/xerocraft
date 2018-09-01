# Standard
import logging
from datetime import date, datetime, timedelta, time
from decimal import Decimal

# Third Party
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.urls import reverse
from django.contrib.sites.models import Site
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import localtime

# Local
from members.models import Member
from kmkr.models import (
    Track, PlayLogEntry,
    UnderwritingQuote, UnderwritingBroadcastSchedule, UnderwritingDeal, UnderwritingBroadcastLog
)
import members.notifications as notifications

__author__ = 'Adrian'

logger = logging.getLogger("kmkr")


def unused(x): x  # To suppress unused argument warnings.


@receiver(post_save, sender=PlayLogEntry)
def log_underwriter_broadcasts(sender, **kwargs):
    unused(sender)
    try:
        # if kwargs.get('created', True):
        ple = kwargs.get('instance')  # type: PlayLogEntry

        if ple.track is None:
            # The log entry is for a track that wasn't played from RadioDJ.
            # I.e. it was something played from a record, phone, etc.
            return

        if ple.track.track_type != Track.TYPE_COMMERCIAL:
            return

        deals = UnderwritingDeal.objects.filter(
            quote__track_id=ple.track.radiodj_id,
            start_date__lte=ple.start.date(),
            end_date__gte=ple.start.date()
        ).all()

        if len(deals) == 0:
            logger.error("Could not find associated deal for {}".format(ple.track))
            return
        elif len(deals) == 1:
            deal = deals[0]
            UnderwritingBroadcastLog.objects.update_or_create(
                deal=deal,
                when_read=ple.start,
                defaults={'schedule': deal.quote.best_schedule_match(ple.start)}
            )
        else:
            logger.error("{} is associated with too many current deals.".format(ple.track))

    except Exception as e:
        logger.error("Problem in log_underwriter_broadcasts: %s", str(e))

