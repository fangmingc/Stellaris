from django.shortcuts import HttpResponse, render
from django.urls import path


class AutomodelConfig:
    """针对每一个加载的model的具体处理"""

    def __init__(self, model_class):
        self.model_name = model_class._meta.model_name
        self.app_name = model_class._meta.app_label

    def get_urls(self):
        """获取url"""
        url_list = [
            path('', self.show_list, name="%s_%s_show" % (self.app_name, self.model_name)),
            path('add/', self.add_list, name="%s_%s_add" % (self.app_name, self.model_name)),
            path('<int:id>/change/', self.change_list, name="%s_%s_change" % (self.app_name, self.model_name)),
            path('<int:id>/delete/', self.delete_list, name="%s_%s_delete" % (self.app_name, self.model_name)),
        ]
        return url_list, None, None

    def show_list(self, request, *args, **kwargs):
        """视图函数--展示"""
        data = self.model_name + "展示页面"

        return render(request, "automodel/show_list.html", {"data": data})

    def add_list(self, request, *args, **kwargs):
        return HttpResponse("添加列表")

    def change_list(self, request, *args, **kwargs):
        return HttpResponse("更改列表")

    def delete_list(self, request, *args, **kwargs):
        return HttpResponse("删除列表")


class AutomodelSite:
    """配置每一个model的路由"""

    def __init__(self):
        self._registry = {}

    def register(self, model_class, config_class=None):
        """将model注册"""
        if not config_class:
            config_class = AutomodelConfig
        self._registry[model_class] = config_class(model_class)

    def get_urls(self):
        """分发url"""
        url_patterns = []

        for model_class, config_obj in self._registry.items():
            url_patterns.append(
                path("%s/%s/" % (config_obj.app_name, config_obj.model_name), config_obj.get_urls())
            )

        return url_patterns

    @property
    def urls(self):
        """获取所有注册后的url"""
        return self.get_urls(), None, "automodel"


site = AutomodelSite()

