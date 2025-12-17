from django.apps import apps
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin, UserManager
from django.db import models

class StudentManager(UserManager):

    def _create_user_object(self, username, email, password, **extra_fields):
        if not username:
            raise ValueError("The given username must be set")
        # Lookup the real model class from the global app registry so this
        # manager method can be used in migrations. This is fine because
        # managers are by definition working on the real model.
        GlobalUserModel = apps.get_model(
            self.model._meta.app_label, self.model._meta.object_name
        )
        username = GlobalUserModel.normalize_username(username)
        user = self.model(username=username, **extra_fields)
        return user


class Student(AbstractBaseUser, PermissionsMixin):
    
    #学号作为主键
    username = models.CharField(
        max_length=12, primary_key=True,unique=True,
        verbose_name='学号'
    )

    # 没有密码
    password = None

    # is_active是必须定义的，Django中许多内置的方法都会用到这个字段
    is_active = models.BooleanField(default=True, verbose_name='激活')
    is_staff = models.BooleanField(default=False, verbose_name='管理员')

    name = models.CharField(max_length=50, verbose_name='姓名',null=True)
    login_count = models.SmallIntegerField(default=0, verbose_name='登录计数')

    USERNAME_FIELD = 'username'
    # 指定在终端使用命令create_superuser时提示用户需要填写哪些字段，空则默认只有username和password两个字段
    REQUIRED_FIELDS = []

    # 需要重新定义一个新的objects对象
    objects = StudentManager()

    # 函数与默认保持一致
    def get_full_name(self):
        return self.name
    
    def get_short_name(self):
        return self.username
    

class OneSurvey(models.Model):

    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='填写人')
    submit_login = models.SmallIntegerField(verbose_name='填写时登录计数',null=True)

    is_small = models.BooleanField(default=False, verbose_name='小问卷')
    score = models.SmallIntegerField(default=0, verbose_name='分数')
    answers = models.JSONField(verbose_name='答案', null=True)
    feedbacks = models.JSONField(verbose_name='反馈', blank=True, null=True)
    submit_time = models.DateTimeField(auto_now_add=True, verbose_name='提交时间')

    class Meta:
        ordering = ['-submit_time']
        verbose_name = '问卷'
        verbose_name_plural = '问卷'


class OldNames(models.Model):

    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name='账户')
    name = models.CharField(max_length=50, verbose_name='姓名',null=True)
    life_end_time = models.DateTimeField(auto_now_add=True, verbose_name='被替换时间',primary_key=True)
    murder_login = models.SmallIntegerField(verbose_name='改名时登录计数',null=True)


