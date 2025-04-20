from django.db import models
from users.models import User
from .utils import send_email_notification
import expenses.common.messages as app_messages
import expenses.common.constants as app_constants


# Create your models here.
class Group(models.Model):
    group_name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.group_name


class GroupMember(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    member = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_owner = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.member.username} - {self.group.group_name}'


class Expense(models.Model):
    name = models.CharField(max_length=100, default="user_expense")
    balance_amt = models.DecimalField(max_digits=10, decimal_places=2)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)
    status = models.CharField(max_length=10, choices=app_constants.EXPENSE_STATUS_CHOICES, default='Pending')
    expense_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.name} - {self.expense_by.username}"


class ExpenseSplit(models.Model):
    expense_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    expense = models.ForeignKey(Expense, on_delete=models.CASCADE)
    split_type = models.CharField(max_length=50, choices=app_constants.SPLIT_CHOICES, default="equal")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_outstanding = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(max_length=10, choices=app_constants.EXPENSE_STATUS_CHOICES, default='Pending')
    settled = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Expense between {self.expense.expense_by.username} and {self.expense_user.username}'

    def save(self, *args, **kwargs):
        subject = app_messages.EXPENSE_NOTIFICATION_MAIL_SUBJECT
        if self.status == app_constants.SplitExpenseStatus.PAID.value and self.expense.expense_by.id != self.expense_user.id:
            email = self.expense.expense_by.email
            message = app_messages.EXPENSE_SETTLED_EMAIL_BODY.format(
                lender=self.expense.expense_by.username,
                amount=self.amount,
                user=self.expense_user.username
            )
        else:
            email = self.expense_user.email
            message = app_messages.EXPENSE_ADDED_NOTIFICATION.format(
                username=self.expense.expense_by.username,
                balance=self.balance_outstanding,
                expense_name=self.expense.name
            )
        send_email_notification.apply_async(kwargs=dict(email=email, subject=subject, message=message))
        super().save(*args, **kwargs)


class Settlement(models.Model):
    payment_id = models.CharField(max_length=20, null=False, blank=False, unique=True)
    expense_split = models.ForeignKey(ExpenseSplit, related_name='split_settlements', on_delete=models.DO_NOTHING,
                                      null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=app_constants.SETTLEMENT_STATUS_CHOICES, default='Pending')
    is_offline = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)
    deleted_on = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Settlement of amount : {self.amount} for {self.expense_split.expense.name} : {self.status}'
