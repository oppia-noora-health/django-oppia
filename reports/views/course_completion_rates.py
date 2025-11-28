from django.contrib.admin.views.decorators import staff_member_required
from django.http.response import Http404
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from oppia.models import Course
from summary.models import UserCourseSummary
from oppia.models import Tracker, Media

@method_decorator(staff_member_required, name='dispatch')
class CourseCompletionRatesView(TemplateView):

    def get(self, request, course_id):
        try:
            course = Course.objects.get(pk=course_id)
        except Course.DoesNotExist:
            raise Http404

        users_completed = []
        users_incompleted = []

        course_activities = course.get_no_activities()
        total_sections = course.get_no_sections()
        course_quizzes = course.get_no_quizzes()
        course_medias = course.get_no_media()

        excluded_user_ids = UserCourseSummary.get_excluded_users().values_list('id', flat=True)
        users_stats = UserCourseSummary.objects \
            .exclude(user__in=excluded_user_ids) \
            .filter(course=course_id).order_by('user')

        for user_stats in users_stats:
            profile = getattr(user_stats.user, 'userprofile', None)
            user_activities = user_stats.completed_activities
            sections_completed = Course.get_sections_completed(course, user_stats.user) or 0
            user_quizzes = user_stats.quizzes_passed or 0
            user_points = user_stats.points or 0
            user_badges = user_stats.badges_achieved or 0
            user_mediaviewed = user_stats.media_viewed or 0
            pretest_score = user_stats.pretest_score or 0
            posttest_score = Course.get_post_test_score(course, user_stats.user) or 0
            score_difference = Course.get_score_difference(course, user_stats.user) or 0

            user_obj = {
                'user': user_stats.user,
                'facility': profile.get_facility() if profile else None,
                'designation': profile.get_designation() if profile else None,
                'pretest_score': pretest_score,

                'activities_completed': user_activities,
                'total_activities': course_activities,
                'completion_percent': (user_activities * 100 / course_activities) if course_activities else 0,

                'sections_completed': sections_completed,
                'total_sections': total_sections,
                'section_completion_percent': (sections_completed * 100 / total_sections) if total_sections else 0,

                'quizzes_completed': user_quizzes,
                'total_quizzes': course_quizzes,
                'quiz_completion_percent': (user_quizzes * 100 / course_quizzes) if course_quizzes else 0,

                'medias_viewed': user_mediaviewed,
                'total_medias': course_medias,
                'media_viewed_percent': (user_mediaviewed * 100 / course_medias) if course_medias else 0,

                'points': user_points,
                'badges': user_badges,

                'posttest_score': posttest_score,

                'score_difference': score_difference,
            }

            if user_activities >= course_activities:
                users_completed.append(user_obj)
            else:
                users_incompleted.append(user_obj)
        
        combined_users = users_completed + users_incompleted

        return render(request, 'reports/course_completion_rates.html', {
            'course': course,
            'users_enroled_count': len(users_completed) + len(users_incompleted),
            'users_completed': users_completed,
            'users_incompleted': users_incompleted,
            'all_users': combined_users,  # Add this
        })

