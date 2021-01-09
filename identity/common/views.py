from django.shortcuts import render

from .models import Provider


def homepage(request):
    return render(request, 'homepage.html', {
        'providers': Provider.objects.filter(active=True)
    })
