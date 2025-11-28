from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from oppia.models import Course, Award
from oppia.utils.filters import CourseFilter
from summary.models import UserCourseSummary


@method_decorator(staff_member_required, name='dispatch')
class CompletionRatesView(TemplateView):

    def get(self, request):
        # Get all non-archived and non-draft courses
        courses = Course.objects.filter(
            CourseFilter.IS_NOT_ARCHIVED & CourseFilter.IS_NOT_DRAFT
        ).order_by('title')

        # Get excluded user IDs (admin/superusers/report-excluded)
        excluded_user_ids = UserCourseSummary.get_excluded_users().values_list('id', flat=True)

        courses_list = []

        for course in courses:
            obj = {'course': course}

            # Total users enrolled (excluding excluded users)
            total_users = UserCourseSummary.objects.filter(
                course=course
            ).exclude(user__in=excluded_user_ids).count()

            # Users who achieved the "Diamond Badge" for this course
            diamond_users = Award.objects.filter(
                user__usercoursesummary__course=course,
                badge__name__iexact="Diamond Badge"
            ).exclude(user__in=excluded_user_ids).values('user').distinct().count()

            # Calculate completion rate based on Diamond Badge
            if total_users > 0:
                completion_rate = (diamond_users / total_users) * 100
            else:
                completion_rate = 0

            obj['enroled'] = total_users
            obj['completion'] = completion_rate  # ✅ Keep variable name as "completion"
            courses_list.append(obj)

        return render(request, 'reports/completion_rates.html', {
            'courses_list': courses_list
        })
