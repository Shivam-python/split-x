import hashlib
import hmac

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task(bind=True, queue=settings.NOTIFICATION_QUEUE)
def send_email_notification(self, **kwargs):
    """
    Helper for sending email notifications of all sorts
    """
    email = kwargs.get("email")
    subject = kwargs.get("subject")
    message = kwargs.get("message")
    send_mail(subject, message, settings.EMAIL_HOST_USER, [email])


def generate_hmac_signature(user_id, expense_id, payment_uid, secret_key):
    message = f"{user_id}:{expense_id}:{payment_uid}"
    return hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()


def verify_hmac_signature(user_id, expense_id, payment_uid, provided_signature, secret_key):
    expected_signature = generate_hmac_signature(user_id, expense_id, payment_uid, secret_key)
    return hmac.compare_digest(expected_signature, provided_signature)
