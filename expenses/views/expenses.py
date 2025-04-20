import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework_simplejwt.authentication import JWTAuthentication

from expenses import helpers as helper
from expenses.common import messages as app_messages
from expenses.permissions import IsSelfOrExpenseAdmin
from expenses.serializers import ExpenseSerializer, SettlementListSerializer

from splitwise_app.utils.response_util import ResponseHandler

logger = logging.getLogger('expenses')


class ExpenseViewSet(viewsets.ViewSet):
    authentication_classes = [JWTAuthentication]
    # permission_classes = [IsAuthenticated]

    def get_permissions(self):

        if self.action == 'user_expense_settlements':
            permission_list = [IsSelfOrExpenseAdmin]
        else:
            permission_list = [IsAuthenticated]

        return [permission() for permission in permission_list]

    def list(self, request):
        try:
            expenses = helper.fetch_user_expense(request)
            if not expenses:
                raise NotFound(app_messages.EXPENSE_NOT_FOUND)

            result = []
            for expense in expenses:
                owed, borrowed = helper.fetch_expense_split(expense, request)
                exp_dict = {
                    "expense_name": expense.name,
                    "expense_id": expense.id,
                    "owed_expenses": helper.fetch_owed_exp_breakup(owed),
                    "borrowed_expenses": helper.fetch_borrowed_exp_breakup(borrowed),
                }
                result.append(exp_dict)

            return ResponseHandler.success(
                message=app_messages.EXPENSE_DETAILS_RETRIEVED,
                data=result
            )
        except NotFound as nfe:
            logger.error(f"API VIEW - LIST EXPENSES : ERROR {str(nfe)}")
            return ResponseHandler.exception(
                message=str(nfe),
                data=None,
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"API VIEW - LIST EXPENSES : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=f"Unexpected error: {str(e)}",
                data=None
            )

    def retrieve(self, request, pk=None):  # pk = expense_id
        try:
            expense = helper.fetch_user_expense(request, expense_id=pk)
            if not expense:
                raise NotFound(app_messages.EXPENSE_NOT_FOUND)

            splits = helper.fetch_expense_split_details(expense)
            result = {
                "expense_name": expense.name,
                "expense_id": expense.id,
                "amount": expense.balance_amt,
                "splits": splits,
            }

            return ResponseHandler.success(
                message=app_messages.EXPENSE_DETAILS_RETRIEVED,
                data=result
            )

        except NotFound as nf:
            logger.error(f"API VIEW - EXPENSES DETAIL : ERROR {str(nf)}")
            return ResponseHandler.exception(
                message=str(nf),
                data=[],
                status_code=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"API VIEW - EXPENSES DETAIL : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=f"Unexpected error: {str(e)}",
                data=None
            )

    def create(self, request):
        try:
            data = request.data.copy()
            expense_by = data.get("expense_by", request.user.id)
            data.setdefault("expense_by", expense_by)

            serializer = ExpenseSerializer(data=data)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return ResponseHandler.success(
                message=app_messages.EXPENSE_ADDED_SUCCESSFULLY,
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )

        except ValidationError as ve:
            logger.error(f"API VIEW - ADD EXPENSES DATA : VALIDATION ERROR {str(ve.detail)}")
            return ResponseHandler.exception(
                message="Validation failed",
                data=ve.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"API VIEW - ADD EXPENSES DATA : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=f"Unexpected error: {str(e)}",
                data=None
            )

    @action(detail=False, methods=["GET"], url_path="(?P<user_id>[^/.]+)/expense-settlement/(?P<expense_id>[^/.]+)")
    def user_expense_settlements(self, request, user_id, expense_id):
        try:
            settlements = helper.fetch_user_settlements_for_expense(user_id=user_id, expense_id=expense_id)
            if settlements:
                serialized_settlements = SettlementListSerializer(settlements, many=True).data
            else:
                serialized_settlements = []

            return ResponseHandler.success(
                message=app_messages.USER_EXPENSE_SETTLEMENTS_DATA_FETCHED,
                data=serialized_settlements
            )
        except Exception as e:
            logger.error(f"API VIEW - FETCH USER EXPENSES SETTLEMENTS : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=app_messages.ERROR_FETCHING_EXPENSE_SETTLEMENT_DATA,
                data=[],
                status_code=status.HTTP_400_BAD_REQUEST
            )
