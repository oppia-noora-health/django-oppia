import datetime
from django.contrib.auth.models import User
from django.utils import timezone

from oppia.badges.base_badge import BaseBadge
from oppia.models import Tracker, Activity, Award, AwardCourse


class BadgeActivityCompletionPercent(BaseBadge):
    """
    Awards badges based on % of activity completion in a course.
    Badges are awarded progressively at:
    - Silver: ≥33%
    - Gold: ≥66%
    - Diamond: 100%
    """

    def process(self, course, badge_dict, hours):
        """
        badge_dict = {
            'silver': <Badge instance>,
            'gold': <Badge instance>,
            'diamond': <Badge instance>
        }
        """

        all_digests = Activity.objects.filter(section__course=course) \
            .values('digest').distinct()
        total_activities = all_digests.count()
        if total_activities == 0:
            return  # No activities to evaluate

        if hours == 0:
            users = User.objects.filter(tracker__course=course)
        else:
            since = timezone.now() - datetime.timedelta(hours=int(hours))
            users = User.objects.filter(
                tracker__course=course,
                tracker__submitted_date__gte=since
            )

        users = users.distinct()

        for user in users:
            completed_digests = Tracker.objects.filter(
                user=user,
                course=course,
                completed=True,
                digest__in=all_digests
            ).values('digest').distinct().count()

            percent_complete = (completed_digests / total_activities) * 100

            def has_badge(badge_obj):
                return Award.objects.filter(user=user, badge=badge_obj,
                                            awardcourse__course=course).exists()

            # Progressive badge awarding
            if percent_complete >= 33 and not has_badge(badge_dict.get('silver')):
                self.award_progress_badge(course, user, badge_dict.get('silver'), 33)

            if percent_complete >= 66 and has_badge(badge_dict.get('silver')) \
               and not has_badge(badge_dict.get('gold')):
                self.award_progress_badge(course, user, badge_dict.get('gold'), 66)

            if percent_complete >= 100 and has_badge(badge_dict.get('gold')) \
               and not has_badge(badge_dict.get('diamond')):
                self.award_progress_badge(course, user, badge_dict.get('diamond'), 100)

