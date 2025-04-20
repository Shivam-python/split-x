from django.contrib import admin
from .models import User, Friends
from django.contrib.admin.decorators import register


# Register all models to the admin site

@register(User)
class UserAdmin(admin.ModelAdmin):
    search_fields = ("username", "email", "mobile")
    list_display = ["id", "username", "email", "mobile"]
    readonly_fields = ["username", "email", "password", "mobile"]

@register(Friends)
class FriendsAdmin(admin.ModelAdmin):
    search_fields = ("user_1__username", "user_2__username")
    list_display = ["user_1", "user_2"]
    # readonly_fields = ["username", "email", "password", "mobile"]
