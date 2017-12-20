from django.db import models


class Role(models.Model):
    """角色表"""
    title = models.CharField(verbose_name="角色名称", max_length=32)

    def __str__(self):
        return self.title


class Department(models.Model):
    """部门表"""
    caption = models.CharField(verbose_name="部门名称", max_length=32)

    def __str__(self):
        return self.caption


class User(models.Model):
    """用户表"""
    username = models.CharField(verbose_name="用户名", max_length=32)
    password = models.CharField(verbose_name="密码", max_length=32)
    gender = models.IntegerField(verbose_name="性别", choices=((1, '男'), (2, '女'), (3, '未知')))
    email = models.EmailField(verbose_name="邮箱")

    role = models.ManyToManyField(to=Role, verbose_name="用户角色")
    dep = models.ForeignKey(to=Department, verbose_name="所属部门", on_delete=False)

    def __str__(self):
        return self.username


class Host(models.Model):
    """主机表"""
    ip = models.GenericIPAddressField(verbose_name="主机ip", protocol='both')
    dep = models.ForeignKey(to=Department, on_delete=False, verbose_name="所属部门", blank=True, null=True)

    def __str__(self):
        return self.ip


