from django import forms
from captcha.fields import CaptchaField
#from .models import Student

class LoginForm(forms.Form):
    #required_css_class = 'form-group'

    id = forms.CharField(
        label='学号',
        min_length=5,
        max_length=12,
        strip=True
        #widget=forms.TextInput(attrs={'placeholder': '请输入学号'})
    )
    name = forms.CharField(
        label='姓名',
        min_length=2,
        max_length=25,
        strip=True
        #widget=forms.TextInput(attrs={'placeholder': '请输入姓名'})
    )
    captcha = CaptchaField(label='数字验证码')
