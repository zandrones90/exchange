from django import forms
from .models import Post


class PostForm(forms.ModelForm):

    class Meta:
        model = Post
        fields =['permission_user','amount', 'price_per_unit', 'crypto', 'type_of_transaction', 'content']
