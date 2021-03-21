from django.urls import path, include
from django.conf.urls import include
from . import views

urlpatterns=[
    path('', include('authentication.urls')),
    path('post/', views.post_list, name='post_list'),
    path('post/', views.post_detail, name='post_detail'),
    path('post/new/', views.post_new, name='post_new'),
    path('post/edit/', views.post_edit, name='post_edit'),#/<str:pk>
]