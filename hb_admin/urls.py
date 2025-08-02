"""
URL configuration for hb_admin project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render

def api_test_view(request):
    return render(request, 'api_test.html')

def simple_test_view(request):
    return render(request, 'simple_test.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('companies.urls')),
    path('api/', include('policies.urls')),
    path('api/', include('orders.urls')),
    path('api/', include('inventory.urls')),
    path('api/', include('messaging.urls')),
    path('api-test/', api_test_view, name='api_test'),
    path('test/', simple_test_view, name='simple_test'),
]
