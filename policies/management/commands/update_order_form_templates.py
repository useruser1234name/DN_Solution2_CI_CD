from django.core.management.base import BaseCommand
from django.db import transaction
from policies.models import Policy, OrderFormTemplate
from policies.form_builder import FormBuilder


class Command(BaseCommand):
    help = 'Create or update default order form templates for all policies.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Force update even when template exists with fields')

    def handle(self, *args, **options):
        force = options.get('force')
        updated = 0
        created = 0
        with transaction.atomic():
            for policy in Policy.objects.all():
                try:
                    try:
                        template = OrderFormTemplate.objects.get(policy=policy)
                        if force or template.fields.count() == 0:
                            FormBuilder.update_template(template)
                            updated += 1
                        else:
                            # skip if not forced and fields exist
                            continue
                    except OrderFormTemplate.DoesNotExist:
                        FormBuilder.create_template(policy)
                        created += 1
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Failed for policy {policy.id}: {e}"))
            self.stdout.write(self.style.SUCCESS(f"Templates created: {created}, updated: {updated}"))
