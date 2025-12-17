from django.apps import AppConfig
from django.db.models.signals import post_migrate
from .singals import *

class SurveyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'survey'

    def ready(self):
        post_migrate.connect(create_default_student, sender=self)


        
