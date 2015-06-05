from django.db import models
from django.utils import timezone
from datetime import date, timedelta

# TODO: Rework various validate() methods into Model.clean()? See Django's "model validation" docs.

class Tag(models.Model):
    name = models.CharField(max_length=40, help_text="A short name for the tag.")
    meaning = models.TextField(max_length=500, help_text="A discussion of the tag's semantics. What does it mean? What does it NOT mean?")

    def __str__(self):
        return self.name

class Member(models.Model):
    """Represents a Xerocraft member, in their many varieties."""

    first_name = models.CharField(max_length=40)
    last_name = models.CharField(max_length=40)
    user_id = models.CharField(max_length=40, help_text="The user-id the member uses to sign in at Xerocraft.")
    family_anchor = models.ForeignKey('self',
        null=True, blank=True, related_name="family_members", on_delete=models.SET_NULL,
        help_text="If this member is part of a family account then this points to the 'anchor' member for the family.")
    tags = models.ManyToManyField(Tag, blank=True)
    #TODO: active = models.BooleanField(default=True, help_text="System will not generate email to this member while it is inactive.")

    def validate(self):
        if self.family_anchor is not None and len(self.family_members.all()) > 0:
            return False, "A member which points to an anchor should not itself be an anchor."
        return True, "Looks good"

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


def make_TaskMixin(dest_class_alias):
    """This function tunes the mix-in to avoid reverse accessor clashes.
-   The rest of the mix-in is identical for both Task and RecurringTaskTemplate.
-   """

    class TaskMixin(models.Model):
        """Defines fields that are common between RecurringTaskTemplate and Task.
        When a task is created from the template, these fields are copied from the template to the task.
        """

        owner = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="owned_"+dest_class_alias,
            help_text="The member that asked for this task to be created or has taken responsibility for its content.")
        instructions = models.TextField(max_length=2048, blank=True,
            help_text="Instructions for completing the task.")
        short_desc = models.CharField(max_length=40,
            help_text="A short description/name for the task.")
        eligible_claimants = models.ManyToManyField(Member, blank=True, symmetrical=False, related_name="claimable_"+dest_class_alias,
            help_text="Anybody chosen is eligible to claim the task.")
        eligible_tags = models.ManyToManyField(Tag, blank=True, symmetrical=False, related_name="claimable_"+dest_class_alias,
            help_text="Anybody that has one of the chosen tags is eligible to claim the task.")
        reviewer = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL,
            help_text="If required, a member who will review the work once its completed.")
        work_estimate = models.IntegerField(default=0,  #TODO: Make this some sort of float since it's hours instead of minutes.
            help_text="An estimate of how much work this tasks requires, in hours (e.g. 1.25). This is work time, not elapsed time.")
        class Meta:
            abstract = True
            ordering = ['short_desc']
    return TaskMixin

class RecurringTaskTemplate(make_TaskMixin("TaskTemplates")):
    """Uses two mutually exclusive methods to define a schedule for recurring tasks.
    (1) A 'day-of-week vs nth-of-month' matrix for schedules like "every first and third Thursday"
    (2) A 'repeat delay' value for schedules like "every 30 days"
    """

    start_date = models.DateField(help_text="Choose a date for the first instance of the recurring task.")
    suspended = models.BooleanField(default=False, help_text="Additional tasks will not be created from this template while it is suspended.")

    # Weekday of month:
    first = models.BooleanField(default=False)  #, help_text="Task will recur on first weekday in the month.")
    second = models.BooleanField(default=False)  #, help_text="Task will recur on second weekday in the month.")
    third = models.BooleanField(default=False)  #, help_text="Task will recur on third weekday in the month.")
    fourth = models.BooleanField(default=False)  #, help_text="Task will recur on fourth weekday in the month.")
    last = models.BooleanField(default=False)  #, help_text="Task will recur on last weekday in the month. This will be 4th or 5th weekday, depending on calendar.")
    every = models.BooleanField(default=False)  #, help_text="Task recur every week")

    # Day of week:
    monday = models.BooleanField(default=False)  #, help_text="Task will recur on Monday.")
    tuesday = models.BooleanField(default=False)  #, help_text="Task will recur on Tuesday.")
    wednesday = models.BooleanField(default=False)  #, help_text="Task will recur on Wednesday.")
    thursday = models.BooleanField(default=False)  #, help_text="Task will recur on Thursday.")
    friday = models.BooleanField(default=False)  #, help_text="Task will recur on Friday.")
    saturday = models.BooleanField(default=False)  #, help_text="Task will recur a Saturday.")
    sunday = models.BooleanField(default=False)  #, help_text="Task will recur a Sunday.")

    #TODO: repeat_delay = models.SmallIntegerField(null=True, blank=True, help_text="Minimum number of days between recurrences, e.g. 14 for every two weeks.")
    #TODO: on_demand = models.BooleanField(default=False, help_text="If selected, tasks will only be scheduled on demand (subject to the delay constraint), otherwise tasks will be automatically scheduled after delay.")

    def greatest_scheduled_date(self):
        "Of the Tasks that correspond to this template, returns the greatest scheduled_date."

        if len(self.task_set.all()) == 0:
            # Nothing is scheduled yet but nothing can be scheduled before start_date.
            # So, pretend that day before start_date is the greatest scheduled date.
            result = self.start_date + timedelta(days = -1)
            return result

        scheduled_dates = map(lambda x: x.scheduled_date, self.task_set)
        return max(scheduled_dates)

    def date_matches_template(self, d: date):
        """
        :param d: Date to be tested.
        :return: Boolean indicating if d matches the day-of-week and ordinal-in-month specified by the template.
        """
        dow_num = d.weekday() # day-of-week number
        day_matches = (dow_num==0 and self.monday) \
            or (dow_num==1 and self.tuesday) \
            or (dow_num==2 and self.wednesday) \
            or (dow_num==3 and self.thursday) \
            or (dow_num==4 and self.friday) \
            or (dow_num==5 and self.saturday) \
            or (dow_num==6 and self.sunday)

        if not day_matches: return False  # Doesn't match template if day-of-week doesn't match.
        if self.every: return True  # Does match if it happens every week and the day-of-week matches.

        # Otherwise, figure out the ordinal and see if we match it.
        dom_num = d.day
        ord_num = 1
        while dom_num > 7:
            dom_num -= 7
            ord_num += 1
        ordinal_matches = (ord_num==1 and self.first==True) \
            or (ord_num==2 and self.second==True) \
            or (ord_num==3 and self.third==True) \
            or (ord_num==4 and self.fourth==True) \
            or (ord_num==4 and self.last==True) \
            or (ord_num==5 and self.last==True)

        return ordinal_matches

    def create_tasks(self, max_days_in_advance):
        """Creates and schedules new tasks from greatest_scheduled_date() (non-inclusive).
        Stops when scheduling a new task would be more than max_days_in_advance from current date.
        Does nothing if the template is suspended.
        """

        if self.suspended: return

        curr = self.greatest_scheduled_date() + timedelta(days = +1)
        curr = max(curr, date.today())  # Don't create tasks in the past.
        stop = date.today() + timedelta(max_days_in_advance)
        while curr < stop:
            if self.date_matches_template(curr):
                t = Task.objects.create(recurring_task_template = self)
                t.owner = self.owner
                t.instructions = self.instructions
                t.short_desc = self.short_desc
                t.eligible_claimants = self.eligible_claimants.all()
                t.eligible_tags = self.eligible_tags.all()
                t.reviewer = self.reviewer
                t.work_estimate = self.work_estimate
                t.save()
            curr += timedelta(days = +1)

    def validate(self):
        sd = self.start_date
        if self.last and self.fourth:
            return False, "Choose either fourth week or last week, not both."
        if self.every and (self.first or self.second or self.third or self.fourth or self.last):
            return False, "If you choose 'every week' don't choose any other weeks."
        if self.work_estimate < 0:
            # zero will mean "not yet estimated" but anything that has been estimated must have work > 0.
            return False, "Invalid work estimate."
        if self.eligible_claimants==None and self.eligible_tags==None:
            return False, "One or more people and/or one or more tags must be selected."
        return True, "Looks good."

    def __str__(self):
        blank = '\u25CC'
        return "%s [%s%s%s%s%s%s%s]" % (
            self.short_desc,
            "M" if self.monday else blank,
            "T" if self.tuesday else blank,
            "W" if self.wednesday else blank,
            "T" if self.thursday else blank,
            "F" if self.friday else blank,
            "S" if self.saturday else blank,
            "S" if self.sunday else blank,
        )


class Task(make_TaskMixin("Tasks")):

    scheduled_date = models.DateField(null=True, blank=True, help_text="If appropriate, set a date on which the task must be performed.")
    deadline = models.DateField(null=True, blank=True, help_text="If appropriate, specify a deadline by which the task must be completed.")
    #TODO: depends_on should be null/blank True.
    depends_on = models.ManyToManyField('self', symmetrical=False, related_name="prerequisite_for", help_text="If appropriate, specify what tasks must be completed before this one can start.")
    claim_date = models.DateField(null=True, blank=True)
    claimed_by = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="tasks_claimed")
    prev_claimed_by =  models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="+") # Reminder: "+" means no backwards relation.
    #TODO: work_actual = models.IntegerField(default=0, help_text="The actual time worked, in hours (e.g. 1.25). This is work time, not elapsed time.")
    work_done = models.BooleanField(default=False)
    work_accepted = models.NullBooleanField()
    recurring_task_template = models.ForeignKey(RecurringTaskTemplate, null=True, blank=True, on_delete=models.SET_NULL)

    def is_closed(self):
        "Returns True if claimant should receive credit for the task."
        if self.reviewer == None:
            return self.work_done
        else:
            return self.work_done and self.work_accepted

    def is_open(self):
        "Returns True if the task isn't yet completed or if there's a reviewer who hasn't yet accepted it."
        return not self.is_closed()

    def validate(self):
        # TODO: questionable if deadline is set but task is an instance of RecurringTaskTemplate.
        if self.work_accepted and not self.work_done:
            return False, "Work cannot be reviewed before it is marked as completed."
        if self.prev_claimed_by == self.claimed_by:
            return False, "Member cannot claim a task they've previously claimed. Somebody else has to get a chance at it."
        if self.work_estimate < 0:
            # zero will mean "not yet estimated" but anything that has been estimated must have work > 0.
            return False, "Invalid work estimate."
        if self.recurring_task_template is not None and self.scheduled_date is None:
            return False, "A task corresponding to a ScheduledTaskTemplate must have a scheduled date."
        return True, "Looks good."

    def __str__(self):
        return "%s on %s" % (self.short_desc, self.scheduled_date)


class TaskNote(models.Model):

    # Note will become anonymous if author is deleted or author is blank.
    author = models.ForeignKey(Member, null=True, blank=True, on_delete=models.SET_NULL,
        help_text="The member who wrote this note.")
    content = models.TextField(max_length=2048,
        help_text="Anything you want to say about the task. Questions, hints, problems, review feedback, etc.")
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
