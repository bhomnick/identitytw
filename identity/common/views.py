from django.shortcuts import render

from .models import Provider
from .snippets import SNIPPETS


def homepage(request):
    return render(request, 'homepage.html', {
        'providers': Provider.objects.filter(active=True).select_related('category'),
        'snippets': SNIPPETS,
    })
