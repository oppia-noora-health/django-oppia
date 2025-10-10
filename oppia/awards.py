
from oppia import badges
from oppia.models import Badge, BadgeMethod, Course
from oppia.utils.filters import CourseFilter


def courses_completed(hours):
    try:
        badge = Badge.objects.get(ref='coursecompleted')
    except Badge.DoesNotExist:
        print("Badge not found: coursecompleted")
        return False

    courses = Course.objects.filter(CourseFilter.IS_NOT_DRAFT & CourseFilter.IS_NOT_ARCHIVED)

    for course in courses:
        print(course.get_title())
        print(badge.default_method)
        print(hours)

        if badge.default_method \
                == BadgeMethod.objects.get(key='all_activities'):
            badge_awarding = badges.BadgeAllActivities()
        elif badge.default_method \
                == BadgeMethod.objects.get(key='final_quiz'):
            badge_awarding = badges.BadgeFinalQuiz()
        elif badge.default_method \
                == BadgeMethod.objects.get(key='all_quizzes'):
            badge_awarding = badges.BadgeAllQuizzes()
        elif badge.default_method \
                == BadgeMethod.objects.get(key='all_quizzes_plus_percent'):
            badge_awarding = badges.BadgeAllQuizzesPlusPercent()
        else:
            return False  # invalid badge method selected

        badge_awarding.process(course, badge, hours)

    return True

def percent_completion_badge(hours):
    """
    Handles percentage-based badge awarding (Silver, Gold, Diamond)
    using badge ref and the 'badge_activity_completion_percent' method.
    """

    # Fetch badges by 'ref' instead of name
    badge_dict = {}
    for level in ['silver', 'gold', 'diamond']:
        try:
            badge_dict[level] = Badge.objects.get(ref=level)
        except Badge.DoesNotExist:
            print(f"[ERROR] Badge with ref '{level}' not found")
            badge_dict[level] = None  # Set to None to handle gracefully later

    # Ensure the method exists
    try:
        method = BadgeMethod.objects.get(key='badge_activity_completion_percent')
    except BadgeMethod.DoesNotExist:
        print("[ERROR] Method 'badge_activity_completion_percent' not found")
        return False

    # Get all valid courses
    courses = Course.objects.filter(CourseFilter.IS_NOT_DRAFT & CourseFilter.IS_NOT_ARCHIVED)

    for course in courses:
        print(f"[INFO] Processing course: {course.get_title()}")

        badge_awarder = badges.BadgeActivityCompletionPercent()
        if all(badge.default_method == method for badge in badge_dict.values()):
            print(f"[INFO] Attempting to award percentage-based badges for course: {course.get_title()}")
            badge_awarder.process(course, badge_dict, hours)
        else:
            print("[SKIP] One or more badges do not use method 'badge_activity_completion_percent'")

    return True
