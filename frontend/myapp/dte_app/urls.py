from django.urls import path
from . import views

urlpatterns = [
    path('', views.upload, name='upload'),
    path('consult/', views.consult, name='consult'),
    path('iva_summary/', views.iva_summary, name='iva_summary'),
    path('range_summary/', views.range_summary, name='range_summary'),
    path('help/', views.help, name='help'),
    path('send/', views.send, name='send'),
    path('reset/', views.reset, name='reset'),
]