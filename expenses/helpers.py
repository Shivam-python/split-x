import decimal
import logging
import secrets

from .models import Group, GroupMember, Expense, ExpenseSplit, Settlement
from users.models import User
from expenses.common import messages as app_messages, constants as app_constants
from django.db import transaction
from django.db.models import Sum, F
from typing import Union
from rest_framework import status
from rest_framework.response import Response
from .utils import send_email_notification
from celery import shared_task
from django.conf import settings
from rest_framework.exceptions import NotFound

logger = logging.getLogger("expenses")


def response_helper(success: bool, message: str, status: status, data: Union[dict, list] = None):
    """
    Helper for making response body.
    @TODO : Need to create view base class with this function which will catch exception & return response. \
    @TODO : Eliminating need of calling it manually
    """
    return Response(
        {"success": success, "message": message, "data": data}, status=status
    )


def fetch_user_groups(request: object, group_id: Union[str, int] = None) -> object:
    """
    Helper to fetch user groups
    """
    try:

        if group_id:
            try:
                # Ensure the group exists and the user is a member
                groups = Group.objects.get(
                    id=group_id,
                    groupmember__member=request.user
                )
            except Group.DoesNotExist:
                raise NotFound(detail="Group not found or you are not a member of this group.")
        else:
            groups = Group.objects.filter(groupmember__member=request.user).distinct()

    except Exception as e:
        logger.error(f"HELPERS - FETCH USER GROUPS : ERROR {str(e)}")
        groups = None

    return groups


def fetch_group_members(group_id: str):
    group_members = GroupMember.objects.filter(group__id=group_id).values_list("member__username", flat=True)
    return group_members


def fetch_user_expense(request: object, expense_id: Union[str, int] = None, group_id: Union[str, int] = None) -> object:
    """
    Helper to get user expenses.
    """
    try:
        if expense_id:
            expenses = Expense.objects.get(id=expense_id)
        elif group_id:
            expenses = Expense.objects.filter(group__id=group_id)
        else:
            expence_user = request.user
            expenses = [i.expense for i in ExpenseSplit.objects.filter(expense_user=expence_user)]
    except Exception as e:
        logger.error(f"HELPERS - FETCH USER EXPENSES : ERROR {str(e)}")
        expenses = None

    return expenses


def fetch_group_expenses(group: object, request: object) -> tuple:
    """
    Helper to fetch expenses for a group
    """
    member = request.user
    owed_expenses = ExpenseSplit.objects.filter(expense__group=group,
                                                balance_outstanding__gt=0).exclude(expense_user=member, ).aggregate(
        total_balance_outstanding=Sum('balance_outstanding')).get("total_balance_outstanding", 0)
    borrowed_expenses = ExpenseSplit.objects.filter(expense__group=group, balance_outstanding__gt=0,
                                                    expense_user=member).aggregate(
        total_balance_outstanding=Sum('balance_outstanding')).get("total_balance_outstanding", 0)
    return owed_expenses, borrowed_expenses


# expense data helpers
def fetch_expense_split(expense: object, request: object) -> tuple:
    """
    Helper to fetch expense data for a user
    """
    member = request.user
    borrowed_expense = ExpenseSplit.objects.filter(expense=expense, expense_user=member,
                                                   balance_outstanding__gt=0)
    owed_expense_split = ExpenseSplit.objects.filter(expense=expense,
                                                     balance_outstanding__gt=0).exclude(expense_user=member)

    return owed_expense_split, borrowed_expense


def fetch_owed_exp_breakup(owed_expenses: object) -> list:
    """
    Helper to group/aggregate owed expenses data
    """
    owed_exp_details = []
    for debt in owed_expenses:
        exp = {
            "name": debt.expense_user.username,
            "amount": str(debt.amount),
            "balance": str(debt.balance_outstanding),
            "status": debt.status
        }
        owed_exp_details.append(exp)
    return owed_exp_details


def fetch_borrowed_exp_breakup(borrowed_expenses: object) -> list:
    """
    Helper to group/aggregate borrowed expenses data
    """
    borrowed_exp_details = []
    for debt in borrowed_expenses:
        exp = {
            "name": debt.expense_user.username,
            "amount": str(debt.amount),
            "balance": str(debt.balance_outstanding),
            "status": debt.status
        }
        borrowed_exp_details.append(exp)
    return borrowed_exp_details


def fetch_expense_split_details(expense: object) -> object:
    expense_splits = ExpenseSplit.objects.filter(expense=expense)
    splits = []
    for obj in expense_splits:
        splits.append({
            "name": obj.expense_user.username,
            "amount": str(obj.amount),
            "balance": str(obj.balance_outstanding),
            "status": obj.status
        })
    return splits


def notify_user_about_debit(lender: User, user_id: Union[str, int]) -> bool:
    """
    Helper to send due pending notification to a friend
    """
    try:
        user = User.objects.get(id=user_id)
        owed_amt = ExpenseSplit.objects.filter(
            expense__expense_by=lender,
            expense_user__id=user_id
        ).aggregate(
            total_balance_outstanding=Sum('balance_outstanding')).get("total_balance_outstanding", 0)
        if not owed_amt:
            raise Exception("All expenses are paid")

        subject = app_messages.DEBIT_REMINDER_MAIL_SUBJECT
        message = app_messages.EXPENSE_RE3MINDER_MAIL_BODY.format(
            user=user.username.capitalize(),
            amount=round(owed_amt, 2),
            lender=lender.username.capitalize()
        )
        send_email_notification.apply_async(kwargs=dict(email=user.email, subject=subject, message=message))
        return True
    except Exception as e:
        logger.error(f"HELPERS - NOTIFY USER ABOUT DEBIT : ERROR {str(e)}")
        return False


def settle_expenses(expense_ids: list, user_id: int, payment_id: str, amount: decimal.Decimal, payment_status: str,
                    mode: str = None) -> tuple:
    """
    Helper function to settle expenses/dues
    """
    try:
        if payment_status == "Settled":
            with transaction.atomic():
                # Step 1: Fetch all relevant ExpenseSplits
                expense_splits = ExpenseSplit.objects.select_related('expense').filter(
                    expense__id__in=expense_ids,
                    expense_user__id=user_id
                )

                # Step 2: Bulk update ExpenseSplits
                expense_splits.update(
                    balance_outstanding=F('balance_outstanding') - amount,
                    status="Paid" if F('balance_outstanding') - amount == 0 else "Pending",
                    settled=True
                )

                # Step 3: Update Settlements individually
                settlements = Settlement.objects.filter(
                    payment_id=payment_id,
                    expense_split__in=expense_splits,
                    deleted_on__isnull=True
                ).select_related('expense_split')

                for settlement in settlements:
                    settlement.status = 'Settled'
                    settlement.is_offline = mode == "Offline"
                    settlement.save()

            return True,app_messages.EXPENSE_SETTLED
        else:
            with transaction.atomic():
                settlement = Settlement.objects.filter(
                    payment_id=payment_id,
                    deleted_on__isnull=True
                ).first()
                settlement.status = 'Failed'
                settlement.is_offline = mode == "Offline"
                settlement.save()
            return True, app_messages.SETTLEMENT_UPDATED
    except Exception as e:
        logger.error(f"HELPERS - SETTLE EXPENSES : ERROR {str(e)}")
        return False, str(e)


@shared_task(bind=True, queue=settings.NOTIFICATION_QUEUE)
def update_expense_status(self, **kwargs):
    expenses = kwargs.get("expenses")
    for expense_id in expenses:
        if not ExpenseSplit.objects.filter(expense__id=expense_id, status="Pending",
                                           balance_outstanding__gt=0).exists():
            expense_obj = Expense.objects.get(id=expense_id)
            expense_obj.status = "Paid"
            expense_obj.save()
    return True


def get_payment_data(payment_uid):
    settlement = Settlement.objects.filter(payment_id=payment_uid).first()
    if not settlement:
        raise Exception("Invalid payment link")

    return settlement


def gen_unique_pay_id():
    unique_str = secrets.token_hex(8)
    return 'pay_' + unique_str


def create_pending_settlement(data):
    payment_id = gen_unique_pay_id()
    settlement = Settlement.objects.create(
        payment_id=payment_id,
        expense_split=data.get("expense_split"),
        amount=data.get("amount")
    )

    return payment_id


def fetch_user_settlements_for_expense(user_id, expense_id):
    settlements = Settlement.objects.filter(expense_split__expense_user__id=user_id,
                                            expense_split__expense__id=expense_id, deleted_on__isnull=True,
                                            status='Settled').all()
    return settlements
