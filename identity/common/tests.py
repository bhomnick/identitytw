from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.html import escape

from .models import (
    LEGACY_ARC_FULL_SUPPORT,
    LEGACY_ARC_NO_SUPPORT,
    LEGACY_ARC_SEPARATE_SUPPORT,
    NEW_ARC_FULL_SUPPORT,
    NEW_ARC_NO_SUPPORT,
    REGISTRATION_OFFLINE,
    REGISTRATION_ONLINE,
    SERVICE_FULL,
    SERVICE_NONE,
    SERVICE_PARTIAL,
    Category,
    Provider,
)
from .snippets import SNIPPET_FILES, SNIPPETS


def make_provider(category, **overrides):
    fields = {
        'name': 'Example',
        'url': 'https://example.com',
        'category': category,
        'legacy_arc_score': LEGACY_ARC_FULL_SUPPORT,
        'new_arc_score': NEW_ARC_FULL_SUPPORT,
        'service_score': SERVICE_FULL,
        'registration_score': REGISTRATION_ONLINE,
    }
    fields.update(overrides)
    return Provider.objects.create(**fields)


class ProviderScoringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name='Banking', slug='banking')

    def test_full_support_scores_100(self):
        provider = make_provider(self.category)
        self.assertEqual(provider.score, 100)
        self.assertEqual(provider.grade, 'A+')
        self.assertEqual(provider.score_reasons, [])

    def test_penalties_are_summed(self):
        provider = make_provider(
            self.category,
            legacy_arc_score=LEGACY_ARC_SEPARATE_SUPPORT,
            service_score=SERVICE_PARTIAL,
        )
        self.assertEqual(provider.score, 65)
        self.assertEqual(provider.grade, 'D')
        self.assertEqual(
            [str(reason) for reason in provider.score_reasons],
            ['Legacy ARC requires separate UI', 'Some services not available to non-citizens'],
        )

    def test_worst_case_is_an_f(self):
        provider = make_provider(
            self.category,
            legacy_arc_score=LEGACY_ARC_NO_SUPPORT,
            new_arc_score=NEW_ARC_NO_SUPPORT,
            service_score=SERVICE_NONE,
            registration_score=REGISTRATION_OFFLINE,
        )
        self.assertEqual(provider.score, -25)
        self.assertEqual(provider.grade, 'F')
        self.assertEqual(len(provider.score_reasons), 4)

    def test_grade_boundaries(self):
        provider = Provider()
        for score, grade in [(100, 'A+'), (90, 'A'), (80, 'B'), (70, 'C'), (60, 'D'), (50, 'E'), (49, 'F'), (None, '-')]:
            provider.score = score
            with self.subTest(score=score):
                self.assertEqual(provider.grade, grade)

    def test_save_refreshes_updated_timestamp(self):
        provider = make_provider(self.category)
        stale = timezone.now() - timedelta(days=30)
        Provider.objects.filter(pk=provider.pk).update(updated=stale)
        provider.refresh_from_db()
        provider.save()
        self.assertGreater(provider.updated, stale + timedelta(days=29))


# Plain static storage so the tests do not depend on collectstatic having run.
@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class HomepageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name='Shopping', slug='shopping')
        make_provider(category, name='Active Shop', service_score=SERVICE_PARTIAL)
        make_provider(category, name='Dormant Shop', active=False)

    def test_lists_active_providers_only(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Shop')
        self.assertNotContains(response, 'Dormant Shop')

    def test_shows_score_reasons(self):
        response = self.client.get('/')
        self.assertContains(response, 'Some services not available to non-citizens')

    def test_embeds_every_validator_snippet(self):
        response = self.client.get('/')
        self.assertEqual(set(SNIPPETS), set(SNIPPET_FILES))
        for language, snippet in SNIPPETS.items():
            with self.subTest(language=language):
                self.assertTrue(snippet, 'snippet is empty')
                self.assertContains(response, escape(snippet))

    def test_language_switch_sets_cookie(self):
        response = self.client.post('/i18n/setlang/', {'language': 'zh-hant', 'next': '/'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies['django_language'].value, 'zh-hant')
