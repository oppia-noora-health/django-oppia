from django.contrib.admin.views.decorators import staff_member_required
from django.http.response import Http404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from oppia.models import Course, Award
from summary.models import UserCourseSummary
from oppia.models import Tracker, Media
from oppia.models import Cohort, CourseCohort, Participant 
@method_decorator(staff_member_required, name='dispatch')
class CourseCompletionRatesView(TemplateView):

    def get(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise Http404

        cohort_filter = request.GET.get('cohort') 

        course_cohorts = CourseCohort.objects.filter(course=course).select_related("cohort")
        course_cohort_ids = [cc.cohort.id for cc in course_cohorts]

        excluded_user_ids = UserCourseSummary.get_excluded_users().values_list('id', flat=True)

        users_stats = UserCourseSummary.objects.exclude(
            user__in=excluded_user_ids
        ).filter(course=course_id)

        selected_cohort = None
        if cohort_filter and cohort_filter.isdigit():
            cohort_filter = int(cohort_filter)

            # Only filter if that cohort is attached to this course
            if cohort_filter in course_cohort_ids:
                selected_cohort = Cohort.objects.get(id=cohort_filter)

                # Users in this cohort (students only)
                users_in_cohort = Participant.objects.filter(
                    cohort_id=cohort_filter,
                    role=Participant.STUDENT
                ).values_list("user_id", flat=True)

                users_stats = users_stats.filter(user_id__in=users_in_cohort)

        users_completed = []
        users_incompleted = []

        course_activities = course.get_no_activities()
        total_sections = course.get_no_sections()
        course_quizzes = course.get_no_quizzes()
        course_medias = course.get_no_media()

        for user_stats in users_stats:
            profile = getattr(user_stats.user, "userprofile", None)

            user_obj = {
                'user': user_stats.user,
                'facility': profile.get_facility() if profile else None,
                'designation': profile.get_designation() if profile else None,

                'pretest_score': user_stats.pretest_score or 0,
                'activities_completed': user_stats.completed_activities,
                'total_activities': course_activities,
                'completion_percent': (user_stats.completed_activities * 100 / course_activities)
                                        if course_activities else 0,

                'sections_completed': Course.get_sections_completed(course, user_stats.user) or 0,
                'total_sections': total_sections,
                'section_completion_percent': (
                    (Course.get_sections_completed(course, user_stats.user) or 0) * 100 / total_sections
                ) if total_sections else 0,

                'quizzes_completed': user_stats.quizzes_passed or 0,
                'total_quizzes': course_quizzes,
                'quiz_completion_percent': (
                    (user_stats.quizzes_passed or 0) * 100 / course_quizzes
                ) if course_quizzes else 0,

                'medias_viewed': user_stats.media_viewed or 0,
                'total_medias': course_medias,
                'media_viewed_percent': (
                    (user_stats.media_viewed or 0) * 100 / course_medias
                ) if course_medias else 0,

                'points': user_stats.points or 0,
                'badges': user_stats.badges_achieved or 0,
                'posttest_score': Course.get_post_test_score(course, user_stats.user) or 0,
                'score_difference': Course.get_score_difference(course, user_stats.user) or 0,

                # Diamond Badge completion
                'completed_at': (Award.objects.filter(
                    user=user_stats.user,
                    awardcourse__course=course,
                    badge__name__iexact="Diamond Badge"
                ).first().award_date if Award.objects.filter(
                    user=user_stats.user,
                    awardcourse__course=course,
                    badge__name__iexact="Diamond Badge"
                ).exists() else None)
            }

            if user_stats.completed_activities >= course_activities:
                users_completed.append(user_obj)
            else:
                users_incompleted.append(user_obj)

        combined_users = users_completed + users_incompleted

        return render(request, "reports/course_completion_rates.html", {
            "course": course,
            "users_enroled_count": len(combined_users),
            "users_completed": users_completed,
            "users_incompleted": users_incompleted,
            "all_users": combined_users,

            "course_cohorts": course_cohorts,
            "selected_cohort": selected_cohort,
        })
