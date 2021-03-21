from django import forms
from .models import *


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('user', 'ips', 'subprofiles')


class PermissionForm(forms.ModelForm):
    class Meta:
        model = Permission
        fields = ('email', 'permission')


class UserpageForm(forms.ModelForm):
    class Meta:
        model = Userpage
        fields = '__all__'
        exclude = ['user']
