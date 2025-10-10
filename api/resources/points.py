from django.http import JsonResponse
from django.urls.conf import re_path
from django.shortcuts import get_object_or_404

from tastypie.authentication import ApiKeyAuthentication
from tastypie.authorization import ReadOnlyAuthorization
from tastypie.resources import ModelResource
from tastypie.utils import timezone

from api.serializers import PrettyJSONSerializer

from oppia.models import Points, Cohort

class PointsResource(ModelResource):
    class Meta:
        queryset = Points.objects.all().order_by('-date')
        allowed_methods = ['get']
        fields = ['date', 'description', 'points', 'type']
        resource_name = 'points'
        include_resource_uri = False
        authentication = ApiKeyAuthentication()
        authorization = ReadOnlyAuthorization()
        serializer = PrettyJSONSerializer()
        always_return_data = True

    def get_object_list(self, request):
        return super(PointsResource, self) \
            .get_object_list(request) \
            .filter(user=request.user)[:100]

    def dehydrate(self, bundle):
        bundle.data['date'] = bundle.data['date'].strftime("%Y-%m-%d %H:%M:%S")
        return bundle

    def prepend_urls(self):
        return [
            re_path(r"^leaderboard-all/$",
                    self.wrap_view('leaderboard_all'),
                    name="api_leaderboard_all"),
            re_path(r"^leaderboard/$",
                    self.wrap_view('leaderboard'),
                    name="api_leaderboard"),
            re_path(r"^leaderboardcohort/(?P<cohortid>[\d,]+)/$", #changed by namratha
                    self.wrap_view('cohort_leaderboard'),
                    name="api_cohort_leaderboard"),
        ]

    def leaderboard_all(self, request, **kwargs):

        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        if request.is_secure():
            prefix = 'https://'
        else:
            prefix = 'http://'

        response_data = {}
        response_data['generated_date'] = timezone.now()
        response_data['server'] = prefix + request.META['SERVER_NAME']
        leaderboard = Points.get_leaderboard()
        response_data['leaderboard'] = []

        for idx, leader in enumerate(leaderboard):
            leader_data = {}
            leader_data['position'] = idx + 1
            leader_data['username'] = leader.username
            leader_data['first_name'] = leader.first_name
            leader_data['last_name'] = leader.last_name
            leader_data['points'] = leader.total
            leader_data['badges'] = leader.badges
            response_data['leaderboard'].append(leader_data)

        return JsonResponse(response_data)

    def leaderboard(self, request, **kwargs):

        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        if request.is_secure():
            prefix = 'https://'
        else:
            prefix = 'http://'

        response_data = {}
        response_data['generated_date'] = timezone.now()
        response_data['server'] = prefix + request.META['SERVER_NAME']
        leaderboard = Points.get_leaderboard_filtered(request.user,
                                                      count_top=20,
                                                      above=20,
                                                      below=20)
        response_data['leaderboard'] = leaderboard

        return JsonResponse(response_data)
    
    #changed by namratha
    def cohort_leaderboard(self, request, cohortid=None, **kwargs):
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        if request.is_secure():
            prefix = 'https://'
        else:
            prefix = 'http://'

        response_data = {
            'generated_date': timezone.now(),
            'server': prefix + request.META['SERVER_NAME'],
            'cohort_id': cohortid,
            'leaderboard': []
        }

        user_map = {}

        cohort_ids = [int(cid) for cid in cohortid.split(',') if cid.isdigit()]
        for cid in cohort_ids:
            try:
                cohort = Cohort.objects.get(pk=cid)
                leaderboard = cohort.get_leaderboard()
                for leader in leaderboard:
                    username = leader.username
                    if username not in user_map:
                        user_map[username] = {
                            'username': username,
                            'first_name': leader.first_name,
                            'last_name': leader.last_name,
                            'points': leader.total,
                            'badges': leader.badges
                        }
                    else:
                        user_map[username]['points'] += leader.total
                        user_map[username]['badges'] += leader.badges  
            except Cohort.DoesNotExist:
                continue

        # Sort by total points
        sorted_leaders = sorted(user_map.values(), key=lambda x: x['points'], reverse=True)

        for idx, leader_data in enumerate(sorted_leaders):
            leader_data['position'] = idx + 1
            response_data['leaderboard'].append(leader_data)

        return JsonResponse(response_data)
