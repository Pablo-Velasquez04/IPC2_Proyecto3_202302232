from django.urls import path, include

urlpatterns = [
    path('', include('dte_app.urls')),
]