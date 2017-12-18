from types import FunctionType, MethodType

from django.shortcuts import HttpResponse, render, reverse, redirect
from django.urls import path
from django.utils.safestring import mark_safe
from django.forms import ModelForm, widgets as wg
from django.core.paginator import Paginator


class AutomodelConfig:
    """针对每一个加载的model的具体处理"""

    # 可配置参数

    list_display = []       # 显示项
    head_list = []          # 显示项的标题

    show_add_btn = False    # 显示增加按钮

    def __init__(self, model_class):
        self.model_class = model_class
        self.model_name = model_class._meta.model_name
        self.app_name = model_class._meta.app_label

    def get_urls(self):
        """获取url"""
        url_list = [
            path('', self.show_list, name="%s_%s_show" % (self.app_name, self.model_name)),
            path('add/', self.add_list, name="%s_%s_add" % (self.app_name, self.model_name)),
            path('<int:obj_id>/change/', self.change_list, name="%s_%s_change" % (self.app_name, self.model_name)),
            path('<int:obj_id>/delete/', self.delete_list, name="%s_%s_delete" % (self.app_name, self.model_name)),
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

    def get_head_list(self):
        """获取需要展示的信息头部说明"""
        data_list = []
        if self.head_list:
            data_list.extend(self.head_list)
        else:
            for field_name in self.get_list_display():
                if isinstance(field_name, str):
                    verbose_name = self.model_class._meta.get_field(field_name).verbose_name
                else:
                    verbose_name = field_name(self, is_header=True)
                data_list.append(verbose_name)
        return data_list

    # ########## 视图函数 ############
    def show_list(self, request, *args, **kwargs):
        """视图函数--展示"""

        def generate_list(data_list, config_obj):
            """生成展示信息"""
            for data_obj in data_list:
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

        data_list = generate_list(self.model_class.objects.all(), self)

        paginator = Paginator(list(data_list), 2)
        # 自适应的页码变化，一共九条记录，选中的页码居中显示
        # 当前页码
        current_page = int(request.GET.get("page", 1))
        if (current_page < 1) and (current_page > paginator.num_pages):
            current_page = 1

        # 当前最小，最大页码
        min_page = current_page - 4 if current_page > 5 else 1
        max_page = current_page + 4 if current_page < (paginator.num_pages - 4) else paginator.num_pages
        # 当临近首页或尾页的时
        if max_page - min_page < 8:
            # 临近首页时
            if current_page - min_page < 4:
                current_range = range(1, 10)
            # 临近尾页时
            elif max_page - current_page < 4:
                current_range = range(paginator.num_pages - 8, paginator.num_pages + 1)
        # 页码正常情况下
        else:
            current_range = range(min_page, max_page + 1)

        # 当前页码显示内容
        data_list = paginator.page(current_page)

        return render(request, "automodel/show_list.html", {
            "data_list": data_list, "show_add_btn": self.show_add_btn, "add_url": self.get_add_url(),
            "current_url": reverse("%s_%s_show" % (self.app_name, self.model_name)),
            "current_page": current_page, "min_page": min_page, "max_page": max_page, "paginator": paginator
            })

    def add_list(self, request, *args, **kwargs):
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
            return redirect(reverse("%s_%s_show" % (self.app_name, self.model_name)))

    def change_list(self, request, *args, **kwargs):
        class TempModelForm(ModelForm):
            class Meta:
                model = self.model_class
                fields = "__all__"
        obj = self.model_class.objects.filter(id=kwargs.get("obj_id")).first()
        if not obj:
            return HttpResponse("数据不存在！")
        if request.method == "GET":
            form = TempModelForm(instance=obj)
            return render(request, "automodel/change_list.html", {"form": form})
        form = TempModelForm(data=request.POST, instance=obj)
        if not form.is_valid():
            return render(request, "automodel/change_list.html", {"form": form})
        else:
            form.save()
            return redirect(
                reverse("%s_%s_show" % (self.app_name, self.model_name)) + "?page=%s" % request.GET.get("page"))

    def delete_list(self, request, *args, **kwargs):
        obj = self.model_class.objects.filter(id=kwargs.get("obj_id")).first()
        if not obj:
            return HttpResponse("数据不存在！")
        self.model_class.objects.filter(id=kwargs.get("obj_id")).delete()
        return redirect(reverse("%s_%s_show" % (self.app_name, self.model_name)))

    # ############# 定制列表页面显示的列
    def checkbox(self, data_obj=None, is_header=False, config_obj=None):
        """勾选框"""
        if is_header:
            return "选择"
        return mark_safe('<input type="checkbox" value="%s">' % data_obj.pk)

    def delete(self, data_obj=None, is_header=False, config_obj=None):
        """删除按钮"""
        if is_header:
            return "删除"
        return mark_safe('<a href="%s">删除</a>' % config_obj.get_delete_url(data_obj.pk))

    def edit(self, data_obj=None, is_header=False, config_obj=None):
        """编辑按钮"""
        if is_header:
            return "编辑"
        return mark_safe('<a href="%s">编辑</a>' % config_obj.get_change_url(data_obj.pk))

    # ############# 反向获取url
    def get_list_url(self):
        return reverse("%s_%s_show" % (self.app_name, self.model_name))

    def get_add_url(self):
        return reverse("%s_%s_add" % (self.app_name, self.model_name))

    def get_change_url(self, nid):
        return reverse("%s_%s_change" % (self.app_name, self.model_name), args=(nid, ))

    def get_delete_url(self, nid):
        return reverse("%s_%s_delete" % (self.app_name, self.model_name), args=(nid, ))


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
        return self.get_urls(), None, "automodel"


site = AutomodelSite()

