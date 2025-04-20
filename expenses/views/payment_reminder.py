import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from expenses import helpers as helper
from expenses.common import messages as app_messages

logger = logging.getLogger('reminders')


class ReminderViewSet(viewsets.ViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="notify")
    def notify(self, request):
        user_id = request.data.get("user_id")
        lender = request.user

        try:
            helper.notify_user_about_debit(lender, user_id)
            return helper.response_helper(
                success=True,
                message=app_messages.USER_NOTIFIED_ABOUT_DUES,
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"API VIEW - PAYMENT REMINDER : ERROR {str(e)}")
            return helper.response_helper(
                success=False,
                message=f"Failed to send reminder : {str(e)}",
                status=status.HTTP_400_BAD_REQUEST
            )
