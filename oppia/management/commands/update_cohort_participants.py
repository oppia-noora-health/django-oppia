from django.core.management.base import BaseCommand
from oppia.models import Cohort

class Command(BaseCommand):
    help = 'Update cohort participants based on cohort criteria'

    def add_arguments(self, parser):
        parser.add_argument('--cohort_id', type=int, help='ID of the cohort to update')

    def handle(self, *args, **options):
        cohort_id = options.get('cohort_id')

        if cohort_id:
            try:
                cohort = Cohort.objects.get(id=cohort_id)
                students, teachers = cohort.update_participants()
                self.stdout.write(self.style.SUCCESS(
                    f'Cohort {cohort_id} updated: {students} students, {teachers} teachers'))
            except Cohort.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Cohort with ID {cohort_id} does not exist.'))
        else:
            cohorts = Cohort.objects.all()
            for cohort in cohorts:
                students, teachers = cohort.update_participants()
                self.stdout.write(self.style.SUCCESS(
                    f'Cohort {cohort.id} updated: {students} students, {teachers} teachers'))
