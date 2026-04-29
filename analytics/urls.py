from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('upload/', views.upload_results, name='upload'),
    path('course/', views.course_analysis, name='course_analysis'),
    path('category/', views.category_analysis, name='category_analysis'),
    path('backlog/', views.backlog_tracking, name='backlog_tracking'),
    path('nba/', views.nba_report, name='nba_report'),
    path('export/nba/', views.export_nba_excel, name='export_nba'),
    path('export/csv/', views.export_results_csv, name='export_csv'),
]