from automodel.services import automodel

from app01 import models


class UserConfig(automodel.AutomodelConfig):

    def display_gender(self, data_obj=None, is_header=False):
        if is_header:
            return "性别"
        return data_obj.get_gender_display()

    def display_role(self, data_obj=None, is_header=False):
        if is_header:
            return "用户角色"
        role_list = [item.title for item in data_obj.role.all()]

        return ','.join(role_list)

    list_display = ["id", "username", display_gender, "email", "dep", display_role]
    show_add_btn = True
    show_delete_btn = True
    show_edit_btn = True
    show_search_form = True
    show_actions_form = True

    combinatorial_filter = [
        automodel.FilterOption("gender", is_choices=True),
        automodel.FilterOption("dep"),
        automodel.FilterOption("role", is_multi=True),
    ]

    # show_search_form = True
    # search_fields = ["username", "email"]

    # show_actions_form = True

    # def extra_url(self):
    #     from django.urls import path
    #     urls = [
    #         path('report/', self.report_view)
    #     ]
    #     return urls

    # def report_view(self):
    #     from django.shortcuts import HttpResponse
    #     return HttpResponse("自定义额外的url")


automodel.site.register(models.Role)
automodel.site.register(models.Department)
automodel.site.register(models.User, UserConfig)
automodel.site.register(models.Host)

