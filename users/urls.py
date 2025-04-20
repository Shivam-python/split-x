# urls.py

from django.urls import path, include
from rest_framework import routers

import users.views as user_views
from users.views.friends import FriendViewSet

router = routers.DefaultRouter()

router.register('users', user_views.UserViewSet, basename='user')
router.register('friend', user_views.FriendViewSet, basename='friend')

urlpatterns = [
    path('',include(router.urls))
]
