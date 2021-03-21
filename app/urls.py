from . import views
from django.urls import path, include

urlpatterns = [
    path('permission', views.permissionPage, name='permission'),
    path('delete_permission/<str:email>/', views.deletePermission, name='delete_permission'),
    path('delete_post/<str:id>/', views.deletePosts, name='delete_post'),
    path('account/setting', views.accountSettings, name="account_setting"),
    path('account/user', views.account_user, name="account_user"),
    path('account/post', views.account_list, name="account_post"),
    path('account/other', views.account_other, name="account_other"),
    path('account/transactions', views.check_transactions, name="account_transactions"),
    path('account/statistics', views.statistics, name="account_statistics"),
    path('account/', views.account, name="account")
    ]