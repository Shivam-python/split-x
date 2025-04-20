from django.contrib import admin
from .models import *
from django.contrib.admin.decorators import register


# Register your models here.

class GroupMemberInline(admin.TabularInline):
    model = GroupMember
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


@register(Group)
class GroupAdmin(admin.ModelAdmin):
    search_fields = ("group_name",)
    list_display = ["id", "group_name"]
    inlines = [GroupMemberInline]


@register(GroupMember)
class GroupMemberAdmin(admin.ModelAdmin):
    search_fields = ("group__group_name", "member__username", "member__email")
    list_display = ["id", "group", "member"]


class ExpenseSplitInline(admin.TabularInline):
    model = ExpenseSplit
    extra = 0

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


@register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    search_fields = ("name", "expense_by__username", "expense_by__email")
    list_display = ["id", "name", "group", "balance_amt", "status", "expense_by"]
    list_filter = ["status", "group"]
    readonly_fields = ["expense_by", "group", "balance_amt"]
    inlines = (ExpenseSplitInline,)

@register(Settlement)
class SettlementAdmin(admin.ModelAdmin):
    list_display = ['payment_id', 'expense_name', 'expense_split', 'amount', 'status', 'is_offline']


@register(ExpenseSplit)
class ExpenseSplitAdmin(admin.ModelAdmin):
    search_fields = (
        "expense__name", "expense__expense_by__username", "expense__expense_by__email", "expense_user__username",
        "expense_user__email")
    list_display = ["id", "expense", "amount", "expense_user",
                    "balance_outstanding", "status"]
    list_filter = ["status", "expense__group"]
    readonly_fields = ["expense_user", "expense", "amount", "balance_outstanding", "split_type"]
