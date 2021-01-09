from collections import namedtuple

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


ScoringCriteria = namedtuple('ScoringCriteria', 'short_desc long_desc points')


LEGACY_ARC_FULL_SUPPORT = 'legacy_arc_full_support'
LEGACY_ARC_SEPARATE_SUPPORT = 'legacy_arc_separate_support'
LEGACY_ARC_NO_SUPPORT = 'legacy_arc_no_support'
NEW_ARC_FULL_SUPPORT = 'new_arc_full_support'
NEW_ARC_SEPARATE_SUPPORT = 'new_arc_separate_support'
NEW_ARC_NO_SUPPORT = 'new_arc_no_support'
SERVICE_FULL = 'service_full'
SERVICE_PARTIAL = 'service_partial'
SERVICE_NONE = 'service_none'
REGISTRATION_ONLINE = 'registration_online'
REGISTRATION_OFFLINE = 'registration_offline'


CRITERIA = {
    LEGACY_ARC_FULL_SUPPORT: ScoringCriteria(
        _('Full legacy ARC support'),
        _('Fully accepts legacy ARC number in place of ROC ID'),
        0
    ),
    LEGACY_ARC_SEPARATE_SUPPORT: ScoringCriteria(
        _('Legacy ARC support in separate UI'),
        _('Accepts legacy ARC number in a separate UI (passport number, for instance)'),
        -10
    ),
    LEGACY_ARC_NO_SUPPORT: ScoringCriteria(
        _('No legacy ARC support'),
        _('Does not accept legacy ARC numbers'),
        -25
    ),
    NEW_ARC_FULL_SUPPORT:  ScoringCriteria(
        _('Full new ARC support'),
        _('Fully accepts new ARC number in place of ROC ID'),
        0
    ),
    NEW_ARC_SEPARATE_SUPPORT: ScoringCriteria(
        _('New ARC support in separate UI'),
        _('Accepts new ARC number in a separate UI (passport number, for instance)'),
        -10
    ),
    NEW_ARC_NO_SUPPORT: ScoringCriteria(
        _('No new ARC support'),
        _('Does not accept new ARC numbers'),
        -25
    ),
    SERVICE_FULL:  ScoringCriteria(
        _('Full service for all users'),
        _('Provides same service to all users'),
        0
    ),
    SERVICE_PARTIAL: ScoringCriteria(
        _('Some services not available to non-citizens'),
        _('A portion of features not available to non-citizens'),
        -25
    ),
    SERVICE_NONE: ScoringCriteria(
        _('Denies service to non-citizens'),
        _('Denies all services to non-citizens'),
        -50
    ),
    REGISTRATION_ONLINE: ScoringCriteria(
        _('All users may register online'),
        _('All users may register online using the same process'),
        0
    ),
    REGISTRATION_OFFLINE: ScoringCriteria(
        _('Non-citizens require offline registration'),
        _('Non-citizens require additional offline registration steps'),
        -25
    )
}


def _c(*choices):
    return [(c, CRITERIA[c].long_desc) for c in choices]\


class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50)

    class Meta:
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class Provider(models.Model):
    name = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(default=timezone.now)
    updated = models.DateTimeField(default=timezone.now)
    category = models.ForeignKey('Category', on_delete=models.PROTECT)
    url = models.URLField(verbose_name='URL')
    score = models.IntegerField()
    requires_id = models.BooleanField(verbose_name='Provider requires ID validation', default=True)
    legacy_arc_score = models.CharField(max_length=50, choices=_c(
        LEGACY_ARC_FULL_SUPPORT,
        LEGACY_ARC_SEPARATE_SUPPORT,
        LEGACY_ARC_NO_SUPPORT
    ), verbose_name='Legacy ARC Score', help_text='How well does this site support legacy ARC numbers?')
    new_arc_score = models.CharField(max_length=50, choices=_c(
        NEW_ARC_FULL_SUPPORT,
        NEW_ARC_SEPARATE_SUPPORT,
        NEW_ARC_NO_SUPPORT
    ), verbose_name='New ARC Score', help_text='How well does this site support new ARC numbers?')
    service_score = models.CharField(max_length=50, choices=_c(
        SERVICE_FULL,
        SERVICE_PARTIAL,
        SERVICE_NONE
    ), verbose_name='Service Score', help_text='Does this site offer the same services to citizens and ARC holders?')
    registration_score = models.CharField(max_length=50, choices=_c(
        REGISTRATION_ONLINE,
        REGISTRATION_OFFLINE
    ), verbose_name='Registration Score', help_text='Does this site require extra registration steps for non-citizens?')

    @property
    def grade(self):
        if self.score is None:
            return '-'
        if self.score >= 100:
            return 'A+'
        if self.score >= 90:
            return 'A'
        if self.score >= 80:
            return 'B'
        if self.score >= 70:
            return 'C'
        if self.score >= 60:
            return 'D'
        if self.score >= 50:
            return 'E'
        return 'F'

    def update_score(self):
        score = 100
        for criteria in [
            self.legacy_arc_score,
            self.new_arc_score,
            self.service_score,
            self.registration_score
        ]:
            score += CRITERIA[criteria].points
        self.score = score

    def save(self, *args, **kwargs):
        self.update_score()
        self.updated = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
