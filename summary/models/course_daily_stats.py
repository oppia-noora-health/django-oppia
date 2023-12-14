
import datetime
from django.db import models

from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _

from oppia import constants
from oppia.models import Course, Tracker, User


class CourseDailyStats (models.Model):
    course = models.ForeignKey(Course,
                               blank=True,
                               null=True,
                               default=None,
                               on_delete=models.CASCADE)
    day = models.DateField(blank=False,
                           null=False)
    type = models.CharField(max_length=10,
                            null=True,
                            blank=True,
                            default=None)
    total = models.IntegerField(blank=False,
                                null=False,
                                default=0)

    class Meta:
        verbose_name = _(u'CourseDailyStats')
        verbose_name_plural = _(u'CourseDailyStats')
        unique_together = ("course", "day", "type")
        indexes = [
            models.Index(fields=['course', 'day', 'type']),
        ]

    @staticmethod
    def update_daily_summary(course,
                             day,
                             last_tracker_pk=0,
                             newest_tracker_pk=0):
        # range of tracker ids to process

        day_start = datetime.datetime \
            .strptime(day.strftime(constants.STR_DATE_FORMAT) + " 00:00:00",
                      constants.STR_DATETIME_FORMAT)
        day_end = datetime.datetime \
            .strptime(day.strftime(constants.STR_DATE_FORMAT) + " 23:59:59",
                      constants.STR_DATETIME_FORMAT)

        excluded_users = User.objects \
            .filter(Q(is_staff=True) | Q(is_superuser=True) | Q(userprofile__exclude_from_reporting=True)) \
            .distinct().values_list('pk', flat=True)

        course = Course.objects.get(pk=course)
        trackers = Tracker.objects.filter(course=course,
                                          tracker_date__gte=day_start,
                                          tracker_date__lte=day_end,
                                          pk__gt=last_tracker_pk,
                                          pk__lte=newest_tracker_pk) \
                                  .excludes(user__in=excluded_users) \
                                  .values('type') \
                                  .annotate(total=Count('type'))

        for type_stats in trackers:
            stats, created = CourseDailyStats.objects \
                .get_or_create(course=course,
                               day=day,
                               type=type_stats['type'])
            stats.total = (0 if last_tracker_pk == 0 else stats.total) \
                + type_stats['total']
            stats.save()
