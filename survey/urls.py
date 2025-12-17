from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('survey/', views.survey_view, name='survey_root'),
    path('survey/<page>/', views.survey_view, name='survey'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('result/', views.result_view, name='result'),
    path('liuanhuamingyouyicun/', views.control_view, name='control'),
    path('liuanhuamingyouyicun/view/<int:sur_id>/', views.viewsur_view, name='view_survey'),
]
