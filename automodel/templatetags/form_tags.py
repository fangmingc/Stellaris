from django.shortcuts import reverse
from django.template import Library
from django.forms.models import ModelChoiceField

from automodel.services.automodel import site

register = Library()


@register.inclusion_tag("automodel/form.html")
def add_change_form(model_form):
    new_form = []
    for bfield in model_form:
        temp = {"field": bfield, "is_popup": False}
        # 判断是否是有外键的字段
        if isinstance(bfield.field, ModelChoiceField):
            model_class = bfield.field.queryset.model
            # 确保外键的表已注册
            if model_class in site._registry:
                temp["is_popup"] = True
                app_model_name = model_class.model._meta.app_label, model_class._meta.model_name
                temp["pop_url"] = reverse("automodel:{0[0]}_{0[1]}_add".format(app_model_name))
        new_form.append(temp)
    return {"form": new_form}
