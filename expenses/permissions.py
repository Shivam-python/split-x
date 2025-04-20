from expenses.models import Expense, ExpenseSplit, GroupMember

from rest_framework.permissions import BasePermission


class IsSelfOrExpenseAdmin(BasePermission):
    """
    Allow access to admin users, the user himself, or the expense creator.
    """

    def has_permission(self, request, view):
        user_id = view.kwargs.get("user_id")
        expense_id = view.kwargs.get("expense_id")

        # Check if user is the one who created the expense
        if expense_id:
            expense = Expense.objects.filter(id=expense_id).first()
            if expense and expense.expense_by == request.user:
                return True
            if expense and user_id and str(request.user.id) == str(user_id) and ExpenseSplit.objects.filter(expense=expense, expense_user=request.user):
                return True

        # Check if user_id matches
        if user_id and str(request.user.id) == str(user_id):
            return True

        return False


class IsGroupMemberOrExpenseAdmin(BasePermission):
    def has_permission(self, request, view):
        group_id = view.kwargs.get("id")
        if GroupMember.objects.filter(group_id=group_id, member=request.user).exists():
            return True
        return False