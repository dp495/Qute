#数据库初始化
def create_default_student(sender, **kwargs):
    from .models import Student
    if Student.objects.filter(username__contains="TMP").first() is None:
        Student.objects.create_user(username='TMP0000',name='TMP_START')
    if Student.objects.filter(username="SI20131275").first() is None:
        Student.objects.create_user(username='SI20131275',name='管理员',is_staff=True,is_superuser=True)
