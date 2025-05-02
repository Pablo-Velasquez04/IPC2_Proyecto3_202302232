# frontend/myapp/myapp/urls.py
from django.urls import path, include
from . import views  # Importar desde el mismo paquete


urlpatterns = [
    path('', views.upload, name='upload'),
    path('consult/', views.consult, name='consult'),
    path('iva_summary/', views.iva_summary, name='iva_summary'),
    path('range_summary/', views.range_summary, name='range_summary'),
    path('help/', views.help, name='help'),
    path('send/', views.send, name='send'),
    path('reset/', views.reset, name='reset'),
    # Si dte_app tiene sus propias URLs, las incluimos aquí
    path('dte/', include('dte_app.urls')),
    
]