from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class AutomodelConfig(AppConfig):
    name = 'automodel'

    def ready(self):
        autodiscover_modules("automodel")
