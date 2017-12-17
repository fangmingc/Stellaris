from automodel.services import automodel

from app01 import models

automodel.site.register(models.Role)
automodel.site.register(models.Department)
automodel.site.register(models.User)
automodel.site.register(models.Host)

