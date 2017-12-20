from types import FunctionType, MethodType
from functools import wraps
from copy import deepcopy

from django.shortcuts import HttpResponse, render, reverse, redirect
from django.urls import path
from django.utils.safestring import mark_safe
from django.forms import ModelForm
from django.http.request import QueryDict
from django.db.models import Q, ForeignKey, ManyToManyField


from automodel.services.paginator import Pagination


class FilterOption:
    """组合过滤"""

    def __init__(self, field_name, condition=None, is_multi=False, is_choices=False):
        self.field_name = field_name
        self.condition = condition
        self.is_multi = is_multi
        self.is_choices = is_choices

    def get_queryset(self, _field):
        if self.condition:
            if hasattr(_field, "rel"):
                return _field.rel.to.objects.filter(**self.condition)
            elif hasattr(_field, "related_model"):
                # django 2.0
                return _field.related_model.objects.filter(**self.condition)
            else:
                raise Exception("不支持的django版本！")
        else:
            if hasattr(_field, "rel"):
                return _field.rel.to.objects.all()
            elif hasattr(_field, "related_model"):
                # django 2.0
                return _field.related_model.objects.all()
            else:
                raise Exception("不支持的django版本！")

    def get_choices(self, _field):
        return _field.choices


class FilterRow:
    """处理组合搜索数据"""

    def __init__(self, data, option, request):
        self.data = data
        self.option = option
        self.request = request
        self.params = deepcopy(request.GET)

    def __iter__(self):
        self.params._mutable = True

        if self.params.get(self.option.field_name):
            # 当该项条件有选择时，删除已选，生成不包含当前选项条件的url
            current_id_list = self.params.pop(self.option.field_name)
            url = self.request.path_info + '?{0}'.format(self.params.urlencode())
            yield mark_safe("<a href='{0}'>{1}</a>".format(url, "全部"))
            self.params.setlist(self.option.field_name, current_id_list)
        else:
            # 当该项无选择时，直接生成当前的url
            url = self.request.path_info + '?{0}'.format(self.params.urlencode())
            yield mark_safe("<a class='active' href='{0}'>{1}</a>".format(url, "全部"))

        # 循环每一项，对每一项包含的条件进行操作
        for value in self.data:
            # 获取当前url的筛选条件
            current_id_list = self.params.getlist(self.option.field_name)

            # 数据时元组还是对象，需要分开处理
            if self.option.is_choices:
                pk, text = str(value[0]), value[1]
            else:
                pk, text = str(value.pk), str(value)

            # 深拷贝一份临时QueryDict, 避免相同筛选选项下不同条件互相干扰
            _params = deepcopy(self.params)

            # 当该条件已被包含在当前条件，给条件增加active
            if pk in current_id_list:
                # 若为多选，url则为取消该条件
                if self.option.is_multi:
                    current_id_list.remove(pk)
                    _params.setlist(self.option.field_name, current_id_list)
                    url = self.request.path_info + '?{0}'.format(_params.urlencode())
                    yield mark_safe('<a class="active" href="{0}">{1}</a>'.format(url, text))
                # 若为单选，url则不操作
                else:
                    url = self.request.path_info + '?{0}'.format(_params.urlencode())
                    yield mark_safe('<a class="active" href="{0}">{1}</a>'.format(url, text))
            # 当该条件不是当前已选中条件
            else:
                # 若为多选，url则在已有条件上增加该条件
                if self.option.is_multi:
                    current_id_list.append(pk)
                    _params.setlist(self.option.field_name, current_id_list)
                    url = self.request.path_info + '?{0}'.format(_params.urlencode())
                    yield mark_safe('<a href="{0}">{1}</a>'.format(url, text))
                # 若为单选，url则替换原有条件
                else:
                    _params[self.option.field_name] = pk
                    url = self.request.path_info + '?{0}'.format(_params.urlencode())
                    yield mark_safe('<a href="{0}">{1}</a>'.format(url, text))


class ShowList:
    """
    AutomodelConfig的show视图函数逻辑较多，在此拆分其功能
    """
    def __init__(self, config, data_list):
        self.config = config

        self.model_class = config.model_class
        self.list_display = config.get_list_display()
        self.head_list = config.get_head_list()
        self.show_add_btn = config.get_show_add_btn()
        self.add_url = config.get_add_url()

        self.search_key = config.search_key
        self.search_value = config.request.GET.get(config.search_key, '')
        self.show_search_form = config.get_show_search_form()

        self.show_actions_form = config.get_show_actions_form()
        self.actions = config.get_actions()

        self.combinatorial_filter = config.get_combinatorial_filter()

        # 分页展示
        self.pager = Pagination(config.request, len(data_list), per_page_num=5)
        self.data_list = ShowList.generate_list(data_list[self.pager.start:self.pager.end], config)

    @staticmethod
    def generate_list(data_list, config):
        """生成展示信息"""
        for data_obj in data_list:
            yield ShowList.generate_column(data_obj, config)

    @staticmethod
    def generate_column(data_obj, config):
        """生成每一行"""
        for item in config.get_list_display():
            if isinstance(item, str):
                if hasattr(data_obj, item):
                    temp = getattr(data_obj, item)
                else:
                    raise Exception("数据库没有该字段！")
            elif isinstance(item, FunctionType):
                if item.__name__ == "__str__":
                    temp = item(data_obj)
                else:
                    temp = item(config, data_obj)
            else:
                raise Exception("使用了无效字段！")
            yield temp

    def generate_combinatorial_filter(self):
        for option in self.combinatorial_filter:
            _field = self.model_class._meta.get_field(option.field_name)
            if isinstance(_field, ForeignKey):
                yield FilterRow(option.get_queryset(_field), option, self.config.request)
            elif isinstance(_field, ManyToManyField):
                yield FilterRow(option.get_queryset(_field), option, self.config.request)
            else:
                yield FilterRow(option.get_choices(_field), option, self.config.request)


class AutomodelConfig:
    """针对每一个加载的model的具体处理"""

    # 可配置参数
    # 1. 定制显示列
    list_display = []

    def get_list_display(self):
        result = []

        if self.list_display:
            result.extend(self.list_display)
        else:
            result.append(self.model_class.__str__)

        result.insert(0, AutomodelConfig.checkbox)

        if self.get_show_edit_btn():
            result.append(AutomodelConfig.edit)

        if self.get_show_delete_btn():
            result.append(AutomodelConfig.delete)
        return result

    # 2. 定制显示项的表头
    head_list = []

    def get_head_list(self):
        result = []

        if self.head_list:
            result.extend(self.head_list)

        else:
            # 根据展示列生成相应的表头
            for field_name in self.get_list_display():
                if isinstance(field_name, str):
                    verbose_name = self.model_class._meta.get_field(field_name).verbose_name

                elif isinstance(field_name, FunctionType):
                    verbose_name = field_name(self, is_header=True)

                else:
                    verbose_name = "对象"

                result.append(verbose_name)
        return result

    # 3. 是否显示增加按钮
    show_add_btn = False

    def get_show_add_btn(self):
        if self.show_add_btn:
            return True
        return False

    # 4. 是否显示编辑按钮
    show_edit_btn = False

    def get_show_edit_btn(self):
        if self.show_edit_btn:
            return True
        return False

    # 5. 是否显示删除按钮
    show_delete_btn = False

    def get_show_delete_btn(self):
        if self.show_delete_btn:
            return True
        return False

    # 6. 使用何种ModelForm
    model_form_class = None

    def get_model_form_class(self):
        if self.model_form_class:
            return self.model_form_class

        # 使用type创建
        temp_model_form = type('TempModelForm', (ModelForm,), {
            'Meta': type('Meta', (object,), {
                "model": self.model_class,
                "fields": "__all__"
            })
        })

        # 常规定义
        # class TempModelForm(ModelForm):
        #     class Meta:
        #         model = self.model_class
        #         fields = "__all__"

        return temp_model_form

    # 7. 搜索框
    show_search_form = False
    search_fields = []

    def get_show_search_form(self):
        if self.show_search_form:
            return True
        return False

    def get_search_fields(self):
        result = []
        if self.search_fields:
            result.extend(self.search_fields)
        return result

    def get_search_condition(self):
        # 根据所给字段设置模糊查询
        search_key = self.request.GET.get(self.search_key, '')  # 确保查询内容不为None,二者择其一
        condition = Q()
        condition.connector = "OR"
        if search_key and self.get_show_search_form():  # 确保查询内容不为None,二者择其一
            for filed_name in self.get_search_fields():
                condition.children.append(("%s__contains" % filed_name, search_key))
        return condition

    # 8. 自定义批量操作/actions
    show_actions_form = False

    def get_show_actions_form(self):
        if self.show_search_form:
            return True
        return False

    def get_actions(self):
        result = {}
        if self.actions:
            for item in self.actions:
                result[item.__name__] = item.short_description
        return result

    def multi_delete(self, request):
        """批量删除"""
        pk_list = request.POST.getlist("pk")
        self.model_class.objects.filter(pk__in=pk_list).delete()
        return HttpResponse("删除成功")

    multi_delete.short_description = "批量删除"
    actions = [multi_delete, ]

    # 9. 组合搜索
    combinatorial_filter = []

    def get_combinatorial_filter(self):
        result = []
        if self.combinatorial_filter:
            result.extend(self.combinatorial_filter)
        return result

    def __init__(self, model_class):
        self.model_class = model_class
        self.model_name = model_class._meta.model_name
        self.app_name = model_class._meta.app_label
        self.app_model_name = self.app_name, self.model_name
        self.request = None
        self._query_key = "_listfilter"
        self.search_key = "_query"

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

    # #############     视图函数
    def show_list_view(self, request, *args, **kwargs):
        """视图函数--展示"""

        if request.method == "POST":
            func = request.POST.get("action")
            if hasattr(self, func):
                ret = getattr(self, func)(request)
                if ret:
                    return ret
        comb_con = {}
        # 获取URL中GET里面的键
        for key in request.GET.keys():
            # 获取配置中的筛选条件
            for option in self.get_combinatorial_filter():
                # 当GET的键在筛选条件中，则加入筛选条件
                if key == option.field_name:
                    comb_con.setdefault("{0}__in".format(option.field_name), request.GET.getlist(option.field_name))
                    break
        data_list = self.model_class.objects.filter(self.get_search_condition()).filter(**comb_con).distinct()
        content = ShowList(self, data_list)

        return render(request, "automodel/show_list.html", {"content": content})

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

        # 验证修改目标是否存在
        obj = self.model_class.objects.filter(id=kwargs.get("obj_id")).first()
        if not obj:
            return HttpResponse("数据不存在！")
        # get请求获取修改目标的数据
        if request.method == "GET":
            form = self.get_model_form_class()(instance=obj)
            return render(request, "automodel/change_list.html", {"form": form})

        # post请求修改目标的数据
        form = self.get_model_form_class()(data=request.POST, instance=obj)
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
    def checkbox(self, data_obj=None, is_header=False):
        """勾选框"""
        if is_header:
            return "选择"
        return mark_safe('<input type="checkbox" name="pk" value="%s">' % data_obj.pk)

    def delete(self, data_obj=None, is_header=False):
        """删除按钮"""
        if is_header:
            return "删除"
        # 如果有搜索条件,记录跳转
        if self.request.GET.urlencode():
            params = QueryDict(mutable=True)
            params[self._query_key] = self.request.GET.urlencode()
            query_str = '<a href="%s?%s">删除</a>' % (self.get_delete_url(data_obj.pk), params.urlencode())
        else:
            query_str = '<a href="%s">删除</a>' % self.get_delete_url(data_obj.pk)
        return mark_safe(query_str)

    def edit(self, data_obj=None, is_header=False):
        """编辑按钮"""
        if is_header:
            return "编辑"
        # 如果有搜索条件,记录跳转
        if self.request.GET.urlencode():
            params = QueryDict(mutable=True)
            params[self._query_key] = self.request.GET.urlencode()
            query_str = '<a href="%s?%s">编辑</a>' % (self.get_change_url(data_obj.pk), params.urlencode())
        else:
            query_str = '<a href="%s">编辑</a>' % self.get_change_url(data_obj.pk)
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

        for model_class, config in self._registry.items():
            url_patterns.append(
                path("%s/%s/" % (config.app_name, config.model_name), config.urls)
            )

        return url_patterns

    @property
    def urls(self):
        """获取所有注册后的url"""
        return self.get_urls(), "automodel", "automodel"


site = AutomodelSite()

