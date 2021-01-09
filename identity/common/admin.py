from django.contrib import admin

from .models import Category, Provider


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    ordering = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'score']
    fieldsets = (
        ('Details', {
            'fields': ['active', 'name', 'category', 'url', 'created', 'updated']
        }),
        ('Scoring', {
            'fields': ['requires_id', 'legacy_arc_score', 'new_arc_score',
                       'service_score', 'registration_score', 'score', 'grade']
        })
    )
    readonly_fields = ['score', 'grade']
