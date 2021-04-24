from django import forms
from .models import Post


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        fields =['account','amount', 'price', 'type_of_transaction']
