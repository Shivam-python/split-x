import logging

from django.conf import settings
from django.shortcuts import render

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView

from expenses import helpers
from expenses.common import messages as app_messages, constants as app_constants
from expenses.serializers import PaymentLinkSerializer
from expenses.utils import generate_hmac_signature, verify_hmac_signature

from splitwise_app.utils.response_util import ResponseHandler

logger = logging.getLogger('payments')


class SettlementViewSet(viewsets.ViewSet):
    authentication_classes = [JWTAuthentication]

    @action(detail=False, methods=["post"], url_path="settle")
    def simulate_settle_expenses(self, request):
        try:
            payment_id = request.data.get("payment_id")
            payment_status = request.data.get("status")
            mode = request.data.get("mode")
            user_id = request.data.get("user_id")
            payment_obj = helpers.get_payment_data(payment_id)
            expense = payment_obj.expense_split.expense
            expense_ids = [expense.id]
            success, message = helpers.settle_expenses(
                expense_ids=expense_ids,
                user_id=user_id,
                payment_id=payment_id,
                payment_status=payment_status,
                amount=payment_obj.amount,
                mode=mode
            )

            if success and payment_status == 'Settled':
                helpers.update_expense_status.apply_async(kwargs=dict(expenses=expense_ids))
                return render(request, 'payment-success.html', context={
                    'payment_obj': payment_obj
                })
            else:
                return render(request, 'payment-failed.html', context={
                    'payment_obj': payment_obj
                })
        except Exception as e:
            logger.error(f"SIMULATE PAYMENTS API VIEW - SIMULATE SETTLE EXPENSES : ERROR {str(e)}")
            return render(request, 'payment-failed.html')


class PaymentSimulator(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data.copy()
            data.setdefault("user_id", request.user.id)
            serializer = PaymentLinkSerializer(data=data)
            if serializer.is_valid():
                payment_uid = helpers.create_pending_settlement(serializer.validated_data)
                payment_link = self.generate_link(data, payment_uid)
                return ResponseHandler.success(
                    message=app_messages.PAYMENT_LINK_GENERATED_SUCCESSFULLY,
                    data={"payment_link": payment_link}
                )
            else:
                return ResponseHandler.failure(
                    message=app_messages.LINK_GENERATION_FAILED,
                    data=serializer.errors,
                    status_code=status.HTTP_406_NOT_ACCEPTABLE
                )
        except Exception as e:
            logger.error(f"API VIEW - GENERATE PAYMENT LINK : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=app_messages.LINK_GENERATION_FAILED + ' ' + str(e),
                data=None
            )

    def generate_link(self, data, payment_uid):
        user_id = data.get("user_id")
        expense_id = data.get("expense_id")
        signature = generate_hmac_signature(user_id=user_id, expense_id=expense_id, payment_uid=payment_uid,
                                            secret_key=settings.PAYMENT_SIMULATOR_SECRET_KEY)
        payment_link = settings.BASE_URL + app_constants.PAYMENT_LINK_URL.format(payment_uid=payment_uid,
                                                                                 signature=signature)
        return payment_link


class PaymentSummary(APIView):
    def get(self, request, payment_uid):
        try:
            signature = request.GET.get("signature")
            payment_obj = helpers.get_payment_data(payment_uid)
            if not payment_obj or payment_obj.status == 'Failed':
                return render(
                    request,
                    'invalid-link.html',
                    context={"message": app_messages.INVALID_PAYMENT_LINK}
                )
            if payment_obj.status == 'Settled':
                return render(
                    request,
                    'invalid-link.html',
                    context={"message": app_messages.EXPENSE_ALREADY_SETTLED}
                )
            if not verify_hmac_signature(user_id=payment_obj.expense_split.expense_user.id,
                                         expense_id=payment_obj.expense_split.expense.id, payment_uid=payment_uid,
                                         provided_signature=signature,
                                         secret_key=settings.PAYMENT_SIMULATOR_SECRET_KEY):
                return ResponseHandler.failure(
                    message=app_messages.SIGNATURE_VALIDATION_FAILED
                )

            return render(
                request, 'payment-summary.html', context={
                    "payment_obj": payment_obj
                }
            )
        except Exception as e:
            logger.error(f"API VIEW - SHOW SUMMARY : ERROR {str(e)}")
            return render(
                request,
                'invalid-link.html',
                context={"message": app_messages.INVALID_PAYMENT_LINK}
            )
