from automodel.services import automodel

from app01 import models


class UserConfig(automodel.AutomodelConfig):
    list_display = ["id", "username", "password", "dep"]
    show_add_btn = True

    def extra_url(self):
        from django.urls import path
        urls = [
            path('report/', self.report_view)
        ]
        return urls

    def report_view(self):
        from django.shortcuts import HttpResponse
        return HttpResponse("自定义额外的url")


automodel.site.register(models.Role)
automodel.site.register(models.Department)
automodel.site.register(models.User, UserConfig)
automodel.site.register(models.Host)

