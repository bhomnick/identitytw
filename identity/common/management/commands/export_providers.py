"""Dump every provider as JSON, for moving the transparency report out of the database.

    heroku run -a <app> python manage.py export_providers > providers.json
"""
import json

from django.core.management.base import BaseCommand

from common.models import Provider


# Model choice value -> short value used by the file-based site.
CHOICE_VALUES = {
    'legacy_arc_full_support': 'full',
    'legacy_arc_separate_support': 'separate',
    'legacy_arc_no_support': 'none',
    'new_arc_full_support': 'full',
    'new_arc_separate_support': 'separate',
    'new_arc_no_support': 'none',
    'service_full': 'full',
    'service_partial': 'partial',
    'service_none': 'none',
    'registration_online': 'online',
    'registration_offline': 'offline',
}


class Command(BaseCommand):
    help = 'Print all providers (including inactive ones) as a JSON array.'

    def handle(self, *args, **options):
        rows = []
        for p in Provider.objects.select_related('category').order_by('name'):
            rows.append({
                'name': p.name,
                'url': p.url,
                'category': p.category.name,
                'legacy_arc': CHOICE_VALUES[p.legacy_arc_score],
                'new_arc': CHOICE_VALUES[p.new_arc_score],
                'service': CHOICE_VALUES[p.service_score],
                'registration': CHOICE_VALUES[p.registration_score],
                'updated': p.updated.date().isoformat(),
                'created': p.created.date().isoformat(),
                'active': p.active,
            })
        self.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2))
