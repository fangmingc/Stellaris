from types import FunctionType, MethodType
from functools import wraps

from django.shortcuts import HttpResponse, render, reverse, redirect
from django.urls import path
from django.utils.safestring import mark_safe
from django.forms import ModelForm, widgets as wg
from django.http.request import QueryDict


from automodel.services.paginator import Pagination


class ShowList:
    """
    AutomodelConfig的show视图函数逻辑较多，在此拆分其功能
    """
    def __init__(self, config):
        self.config = config

        self.model_class = config.model_class

        self.head_list = config.head_list
        self.list_display = config.get_list_display()

    # TODO: 处理好重名问题
    def get_head_list(self):
        """获取表头"""
        result = []
        if self.head_list:
            result.extend(self.head_list)
        else:
            for field_name in self.list_display:
                if isinstance(field_name, str):
                    verbose_name = self.model_class._meta.get_field(field_name).verbose_name
                else:
                    verbose_name = field_name(self.config, is_header=True)
                result.append(verbose_name)
        return result


class AutomodelConfig:
    """针对每一个加载的model的具体处理"""

    # TODO: 补全可配置参数，modelform,搜索,action
    # 可配置参数
    list_display = []       # 显示项
    head_list = []          # 显示项的标题
    show_add_btn = False    # 显示增加按钮

    def __init__(self, model_class):
        self.model_class = model_class
        self.model_name = model_class._meta.model_name
        self.app_name = model_class._meta.app_label
        self.app_model_name = self.app_name, self.model_name
        self.request = None
        self._query_key = "_listfilter"

    # ######### URL相关
    def wrap(self, view_func):
        """通过视图函数给对象的request赋值"""
        # @wraps
        def inner(request, *args, **kwargs):
            self.request = request
            return view_func(request, *args, **kwargs)
        return inner

    def get_urls(self):
        """获取url"""
        url_list = [
            path('', self.wrap(self.show_list_view), name="%s_%s_show" % self.app_model_name),
            path('add/', self.wrap(self.add_list_view), name="%s_%s_add" % self.app_model_name),
            path('<int:obj_id>/change/', self.wrap(self.change_list_view), name="%s_%s_change" % self.app_model_name),
            path('<int:obj_id>/delete/', self.wrap(self.delete_list_view), name="%s_%s_delete" % self.app_model_name),
        ]
        url_list.extend(self.extra_url())
        return url_list

    def extra_url(self):
        """拓展url"""
        return []

    @property
    def urls(self):
        return self.get_urls(), None, None

    def get_list_display(self):
        """获取需要展示信息列表"""
        data_list = []
        if self.list_display:
            data_list.extend(self.list_display)
        else:
            data_list.append(self.model_class.__str__)
        # 使用self可用于区分方法和函数
        data_list.insert(0, self.checkbox)
        data_list.append(self.edit)
        data_list.append(self.delete)
        return data_list

    # #############     视图函数
    def show_list_view(self, request, *args, **kwargs):
        """视图函数--展示"""
        # TODO: 把内容都转移到ShowList

        operate = ShowList(self)

        def generate_list(_data_list, config_obj):
            """生成展示信息"""
            for data_obj in _data_list:
                yield generate_column(data_obj, config_obj)

        def generate_column(data_obj, config_obj):
            """生成每一行"""
            for item in config_obj.get_list_display():
                if isinstance(item, str):
                    if hasattr(data_obj, item):
                        temp = getattr(data_obj, item)
                    else:
                        raise Exception("数据库没有该字段！")
                # 针对config类
                elif isinstance(item, MethodType):
                    temp = item(config_obj=config_obj, data_obj=data_obj)
                # 针对model
                elif isinstance(item, FunctionType):
                    temp = item(data_obj)
                else:
                    raise Exception("使用了无效字段！")
                yield temp

        # TODO: 数据添加搜索,使用Q的高级用法
        # 分页展示
        data_list = self.model_class.objects.all()
        pager = Pagination(request, len(data_list), per_page_num=2)
        data_list = generate_list(data_list[pager.start:pager.end], self)

        return render(request, "automodel/show_list.html", {
            "head_list": operate.get_head_list(),
            "data_list": data_list,
            "show_add_btn": self.show_add_btn,
            "add_url": self.get_add_url(),
            "pager": pager})

    def add_list_view(self, request, *args, **kwargs):
        class TempModelForm(ModelForm):
            class Meta:
                model = self.model_class
                fields = "__all__"
        if request.method == "GET":
            return render(request, "automodel/add_list.html", {"form": TempModelForm()})
        form = TempModelForm(data=request.POST)
        if not form.is_valid():
            return render(request, "automodel/add_list.html", {"form": form})
        else:
            form.save()
            return redirect(self.get_list_url())

    def change_list_view(self, request, *args, **kwargs):
        """修改视图函数"""
        # TODO: 使用两种方式创建ModelForm
        type('TempModelForm', (ModelForm, ), {})

        class TempModelForm(ModelForm):
            class Meta:
                model = self.model_class
                fields = "__all__"
        # 验证修改目标是否存在
        obj = self.model_class.objects.filter(id=kwargs.get("obj_id")).first()
        if not obj:
            return HttpResponse("数据不存在！")
        # get请求获取修改目标的数据
        if request.method == "GET":
            form = TempModelForm(instance=obj)
            return render(request, "automodel/change_list.html", {"form": form})

        # post请求修改目标的数据
        form = TempModelForm(data=request.POST, instance=obj)
        if not form.is_valid():
            return render(request, "automodel/change_list.html", {"form": form})
        else:
            form.save()
            return redirect(self.get_list_url()+"?%s" % request.GET.get(self._query_key))

    def delete_list_view(self, request, *args, **kwargs):
        """
        删除视图
        """
        # 验证删除目标是否存在
        obj = self.model_class.objects.filter(id=kwargs.get("obj_id")).first()
        if not obj:
            return HttpResponse("数据不存在！")

        self.model_class.objects.filter(id=kwargs.get("obj_id")).delete()
        return redirect(self.get_list_url()+"?%s" % request.GET.get(self._query_key))

    # #############     定制列表页面显示的列
    def checkbox(self, data_obj=None, is_header=False, config_obj=None):
        """勾选框"""
        if is_header:
            return "选择"
        return mark_safe('<input type="checkbox" value="%s">' % data_obj.pk)

    def delete(self, data_obj=None, is_header=False, config_obj=None):
        """删除按钮"""
        if is_header:
            return "删除"
        # 如果有搜索条件,记录跳转
        if self.request.GET.urlencode():
            params = QueryDict(mutable=True)
            params[self._query_key] = self.request.GET.urlencode()
            query_str = '<a href="%s?%s">删除</a>' % (config_obj.get_delete_url(data_obj.pk), params.urlencode())
        else:
            query_str = '<a href="%s">删除</a>' % config_obj.get_delete_url(data_obj.pk)
        return mark_safe(query_str)

    def edit(self, data_obj=None, is_header=False, config_obj=None):
        """编辑按钮"""
        if is_header:
            return "编辑"
        # 如果有搜索条件,记录跳转
        if self.request.GET.urlencode():
            params = QueryDict(mutable=True)
            params[self._query_key] = self.request.GET.urlencode()
            query_str = '<a href="%s?%s">编辑</a>' % (config_obj.get_change_url(data_obj.pk), params.urlencode())
        else:
            query_str = '<a href="%s">编辑</a>' % config_obj.get_change_url(data_obj.pk)
        return mark_safe(query_str)

    # #############     反向获取url
    def get_list_url(self):
        return reverse("automodel:%s_%s_show" % self.app_model_name)

    def get_add_url(self):
        return reverse("automodel:%s_%s_add" % self.app_model_name)

    def get_change_url(self, nid):
        return reverse("automodel:%s_%s_change" % self.app_model_name, args=(nid, ))

    def get_delete_url(self, nid):
        return reverse("automodel:%s_%s_delete" % self.app_model_name, args=(nid, ))


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
                path("%s/%s/" % (config_obj.app_name, config_obj.model_name), config_obj.urls)
            )

        return url_patterns

    @property
    def urls(self):
        """获取所有注册后的url"""
        return self.get_urls(), "automodel", "automodel"


site = AutomodelSite()

