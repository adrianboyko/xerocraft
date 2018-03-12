# Standard
import logging
from datetime import date, datetime, timedelta
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
from members.models import Member, Tagging, VisitEvent, Membership
from tasks.models import Task, Worker, Claim, Work, Nag, RecurringTaskTemplate, TimeAccountEntry
import members.notifications as notifications

__author__ = 'Adrian'

logger = logging.getLogger("tasks")
USER_VOLUNTEER = settings.BZWOPS_TASKS_CONFIG.get("USER_VOLUNTEER", None)


def unused(x): x  # To suppress unused argument warnings.


@receiver(post_save, sender=Tagging)
def act_on_new_tag(sender, **kwargs):
    unused(sender)
    if kwargs.get('created', True):
        pass
        """ TODO: Check to see if this new tagging makes the tagged_member eligible for a task
            they weren't previously eligible for. If so, email them with info.
        """


@receiver(post_save, sender=Member)
def create_default_worker(sender, **kwargs):
    unused(sender)
    if kwargs.get('created', True):
        w, _ = Worker.objects.get_or_create(member=kwargs.get('instance'))


@receiver(pre_save, sender=Claim)
def staffing_update_notification(sender, **kwargs):
    unused(sender)
    try:
        if kwargs.get('created', True):
            claim = kwargs.get('instance')  # type: Claim
            message = None
            if claim.status in [Claim.STAT_UNINTERESTED, Claim.STAT_ABANDONED, Claim.STAT_EXPIRED]:
                message = "{0} will NOT work '{1}' on {2:%a %m/%d}".format(
                    claim.claiming_member.friendly_name,
                    claim.claimed_task.short_desc,
                    claim.claimed_task.scheduled_date
                )
            if claim.status == Claim.STAT_CURRENT and claim.date_verified is not None:
                message = "{0} WILL work '{1}' on {2:%a %m/%d}".format(
                    claim.claiming_member.friendly_name,
                    claim.claimed_task.short_desc,
                    claim.claimed_task.scheduled_date
                )
            if message is not None:
                try:
                    recipient = Member.objects.get(auth_user__username=USER_VOLUNTEER)
                    notifications.notify(recipient, "Staffing Update", message)
                except Member.DoesNotExist:
                    return

    except Exception as e:
        logger.error("Problem sending staffing update.")


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# VISIT
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

# HOST = "http://192.168.1.101:8000"  # For testing
HOST = "https://" + Site.objects.get_current().domain


@receiver(post_save, sender=VisitEvent)
def notify_staff_of_checkin(sender, **kwargs):
    """Notify a staffer of a visitor's paid status when that visitor checks in."""
    # TODO: Per feedback from Annette, don't send notices if it's currently "open house".
    unused(sender)
    try:
        if kwargs.get('created', True):
            visit = kwargs.get('instance')

            # We're only interested in arrivals
            if visit.event_type != VisitEvent.EVT_ARRIVAL:
                return

            if visit.who.is_currently_paid():
                # Let's not overwhelm the staffer with info that doesn't require action.
                # A paid visitor is welcome anytime, so don't notify the staffer.
                return

            recipient = Worker.scheduled_receptionist()
            if recipient is None:
                return

            if visit.debounced():
                vname = "{} {}".format(visit.who.first_name, visit.who.last_name).strip()
                vname = "Anonymous" if len(vname) == 0 else vname
                vstat = "Paid" if visit.who.is_currently_paid() else "Unpaid"
                message = "{}\n{}\n{}".format(visit.who.username, vname, vstat)
                notifications.notify(recipient, "Check-In", message)

    except Exception as e:
        # Makes sure that problems here do not prevent the visit event from being saved!
        logger.error("Problem in note_checkin: %s", str(e))


@receiver(post_save, sender=VisitEvent)
def maintenance_nag(sender, **kwargs):
    unused(sender)
    try:
        visit = kwargs.get('instance')  # type: VisitEvent

        # We're only interested in arrivals
        if visit.event_type != VisitEvent.EVT_ARRIVAL:
            return

        # Only act on a member's first visit of the day.
        start_of_today = localtime(timezone.now()).replace(
            hour=4,  # For the purpose of this nag, I'm going to say that day begins at 4am.
            minute=0,
            second=0,
            microsecond=0,
        )
        num_visits_today = VisitEvent.objects.filter(
            who=visit.who,
            event_type=VisitEvent.EVT_ARRIVAL,
            when__gte=start_of_today,
        ).count()
        if num_visits_today > 1:
            return

        # This gets tasks that are scheduled like maintenance tasks.
        # I.e. those that need to be done every X days, but can slide.
        tasks = Task.objects.filter(
            eligible_claimants=visit.who,
            scheduled_date=date.today(),
            status=Task.STAT_ACTIVE,
            should_nag=True,
            recurring_task_template__repeat_interval__isnull=False,
            recurring_task_template__missed_date_action=RecurringTaskTemplate.MDA_SLIDE_SELF_AND_LATER,
        )

        # We're going to want to send msgs to a manager to let them know that people were asked to do the work.
        # TODO: Shouldn't have a hard-coded userid here. Make configurable, perhaps with tags.
        try:
            mgr = Member.objects.get(auth_user__username=USER_VOLUNTEER)
        except Member.DoesNotExist:
            mgr = None

        # Nag the visitor by sending a notification for each task they could work.
        for task in tasks:  # type: Task

            # Create the nag
            b64, md5 = Member.generate_auth_token_str(
                lambda token: Nag.objects.filter(auth_token_md5=token).count() == 0  # uniqueness test
            )
            nag = Nag.objects.create(who=visit.who, auth_token_md5=md5)
            nag.tasks.add(task)

            # Generate an informative message
            try:
                last_done = Task.objects.filter(
                    scheduled_date__lt=date.today(),
                    status=Task.STAT_DONE,
                    recurring_task_template=task.recurring_task_template,
                ).latest('scheduled_date')
                delta = date.today() - last_done.scheduled_date  # type: timedelta
                message = "This task was last completed {} days ago!".format(delta.days)
            except Task.DoesNotExist:
                message = ""
            message += " If you can complete this task today, please click the link AFTER the work is done."

            relative = reverse('task:note-task-done', kwargs={'task_pk': task.id, 'auth_token': b64})
            # Send the notification
            was_sent = notifications.notify(
                visit.who,
                task.short_desc,
                message,
                url=HOST+relative,
                url_title="I Did It!",
            )

            if was_sent:
                # Let manager know:
                if visit.who != mgr:
                    notifications.notify(
                        mgr,
                        task.short_desc,
                        visit.who.friendly_name + " was asked to work this task.",
                    )
            else:
                # If the notification wasn't sent, then the user wasn't actually nagged.
                nag.delete()

    except Exception as e:
        # Makes sure that problems here do not prevent subsequent processing.
        logger.error("Problem in maintenance_nag: %s", str(e))


@receiver(post_save, sender=VisitEvent)
def notify_manager_re_staff_arrival(sender, **kwargs):
    """Notify the Volunteer Coordinator when a staffer checks in around the time they're scheduled to work a task."""
    unused(sender)
    try:
        if kwargs.get('created', True):
            visit = kwargs.get('instance')  # type: VisitEvent

            # We're only interested in arrivals
            if visit.event_type != VisitEvent.EVT_ARRIVAL:
                return

            try:
                recipient = Member.objects.get(auth_user__username=USER_VOLUNTEER)
            except Member.DoesNotExist:
                return

            if visit.debounced():
                claims = Claim.objects.filter(
                    claiming_member=visit.who,
                    claimed_task__priority=Task.PRIO_HIGH,
                    claimed_task__scheduled_date=datetime.now().date(),
                    status=Claim.STAT_CURRENT,
                    # TODO: Is a window around the claimed start time necessary?
                )

                if len(claims) == 0:
                    return

                task = claims[0].claimed_task  # type: Task
                title = "{} Arrived".format(visit.who.friendly_name)
                message = "Scheduled to work {} at {}".format(
                    task.short_desc,
                    task.window_start_time()

                )
                notifications.notify(recipient, title, message)

    except Exception as e:
        # Makes sure that problems here do not prevent the visit event from being saved!
        logger.error("Problem in notify_manager_re_staff_arrival: %s", str(e))


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# TIME ACCOUNTING
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@receiver(post_save, sender=Work)
@receiver(pre_save, sender=Work)
def credit_time_acct(sender, **kwargs):
    """When a witnessed work entry is created, credit it to the worker's time account."""
    unused(sender)
    try:
        work = kwargs.get('instance')  # type: Work

        if work.pk is None:
            # The work hasn't yet been saved to DB, so we can't link a TimeAccountEntry to it.
            return

        if work.witness is None:
            # We only credit witnessed work
            return

        worker = work.claim.claiming_member.worker  # type: Worker

        try:
            # If there's already an entry for this work, delete it since we'll recreate it.
            TimeAccountEntry.objects.get(work=work).delete()
        except TimeAccountEntry.DoesNotExist:
            pass

        if work.work_start_time is not None:
            acct_entry_when = datetime.combine(work.work_date, work.work_start_time)
        else:
            acct_entry_when = work.work_date

        # Remember: Time accounting is denominated in hours.
        TimeAccountEntry.objects.create(
            work=work,
            explanation="Work done on {}".format(work.work_date),
            worker=worker,
            change=Decimal.from_float(work.work_duration.total_seconds() / 3600.0),
            when=acct_entry_when
        )

    except Exception as e:
        # Makes sure that problems here do not prevent the visit event from being saved!
        logger.error("Problem in credit_time_account: %s", str(e))


@receiver(post_save, sender=Membership)
@receiver(pre_save, sender=Membership)
def debit_time_acct_for_mship(sender, **kwargs):
    """When an x month Work Trade membership is purchased, debit the worker's time account."""
    unused(sender)

    try:
        mship = kwargs.get('instance')  # type: Membership

        if mship.pk is None:
            # The mship hasn't yet been saved to DB, so we can't link a TimeAccountEntry to it.
            return

        if mship.membership_type != Membership.MT_WORKTRADE:
            # This only applies to Work Trade memberships.
            return

        worker = mship.member.worker  # type: Worker

        try:
            # If there's already an entry for this membership, delete it since we'll recreate it.
            TimeAccountEntry.objects.get(play=mship).delete()
        except TimeAccountEntry.DoesNotExist:
            pass

        # REVIEW: This should be two different WT membership types, instead of depending on $price?
        if mship.sale_price == Decimal("25.00"):
            time_cost = Decimal("-6.0")
        elif mship.sale_price == Decimal("10.00"):
            time_cost = Decimal("-9.0")
        else:
            logger.error("Unexpected sale price for mship #%ld", mship.id)
            # Let them have it for 0 hours, until we figure out what happened and make a manual fix.
            time_cost = Decimal("0.0")

        # Remember: Time accounting is denominated in hours.
        TimeAccountEntry.objects.create(
            play=mship,
            explanation="Work-trade membership beginning {}".format(mship.start_date),
            worker=worker,
            change=time_cost,
            when=mship.start_date
        )

    except Exception as e:
        # Makes sure that problems here do not prevent the visit event from being saved!
        logger.error("Problem in debit_time_acct_for_mship: %s", str(e))
