from django.urls import path
from . import views

urlpatterns = [
    path('', views.accueil, name='home'),
    path('manager/dashboard/', views.dashboard_demandes, name='dashboard_demandes'),
    path('service/<int:service_id>/', views.detail_service, name='detail_service'),
]
