# tasks.py
import logging

from celery import shared_task
from django.db.models import Sum
from expenses.models import ExpenseSplit
import expenses.common.messages as app_messages
from .utils import send_email_notification
from django.conf import settings

logger = logging.getLogger("expenses")

@shared_task(queue=settings.NOTIFICATION_QUEUE)
def weeekly_notification_task():
    expense_splits = ExpenseSplit.objects.filter(
        balance_outstanding__gt=0
    ).values(
        'expense__expense_by',
        'expense__expense_by__username',
        'expense_user__email',
        'expense_user__username'
    ).annotate(
        total_amount=Sum('amount')
    )

    for split in expense_splits:
        try:
            lender = split["expense__expense_by__username"]
            borrower_email = split['expense_user__email']
            borrower_name = split["expense_user__username"] if split.get("expense_user__username") else "Split-X User"
            amount = split['total_amount']

            subject = app_messages.DEBIT_REMINDER_MAIL_SUBJECT
            message = app_messages.EXPENSE_RE3MINDER_MAIL_BODY.format(
                user=borrower_name.capitalize(),
                amount=round(amount, 2),
                lender=lender.capitalize()
            )
            send_email_notification(email=borrower_email, subject=subject, message=message)
        except Exception as e:
            logger.error(f"TASKS - WEEKLY NOTIFICATION TASK : ERROR {str(e)}")
        return True
