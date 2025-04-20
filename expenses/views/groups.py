import logging

from rest_framework import (status, viewsets, mixins)
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import serializers
import expenses.helpers as helper
from expenses.models import Group
from expenses.permissions import IsGroupMemberOrExpenseAdmin
from expenses.serializers import GroupSerializer, GroupMemberSerializer
from rest_framework.decorators import action

from splitwise_app.utils.pagination_utils import StandardResultsSetPagination
from splitwise_app.utils.response_util import ResponseHandler
from expenses.common import messages as app_messages

logger = logging.getLogger('groups')


class GroupAPIView(viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin, mixins.ListModelMixin):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

    def get_permissions(self):
        if self.action == 'expense_list':
            permission_list = [IsGroupMemberOrExpenseAdmin]
        else:
            permission_list = [IsAuthenticated]
        return [permission() for permission in permission_list]

    def list(self, request, *args, **kwargs):
        groups = helper.fetch_user_groups(request)

        if not groups:
            return ResponseHandler.failure(
                message=app_messages.GROUP_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND
            )

        paginator = StandardResultsSetPagination()
        paginated_groups = paginator.paginate_queryset(groups, request)
        result = [
            {
                "group_name": g.group_name,
                "group_id": g.id,
                "owed_expenses": helper.fetch_group_expenses(g, request)[0] or 0,
                "borrowed_expenses": helper.fetch_group_expenses(g, request)[1] or 0
            } for g in paginated_groups
        ]
        result = paginator.get_paginated_response(result)
        return ResponseHandler.success(
            message=app_messages.GROUP_DATA_FOUND,
            data=result
        )

    def retrieve(self, request, id=None, *args, **kwargs):
        try:
            group = helper.fetch_user_groups(request, group_id=id)

            if not group:
                return ResponseHandler.failure(
                    message=app_messages.GROUP_NOT_FOUND,
                    status_code=status.HTTP_404_NOT_FOUND
                )

            members = helper.fetch_group_members(group.id)

            result = {
                "group_name": group.group_name,
                "description": group.description,
                "members": members,
                # "created_on": group.created_on
            }

            return ResponseHandler.success(
                message=app_messages.GROUP_DATA_FOUND,
                data=result
            )
        except Exception as e:
            logger.error(f"API VIEW - FETCH GROUP DETAIL : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=app_messages.GROUP_NOT_FOUND
            )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            group = serializer.save()

            # Prepare member data
            member_ids = request.data.get('member', [])
            if request.user.id not in member_ids:
                member_ids.append(request.user.id)

            member_payload = {
                'group': group.id,
                'member': member_ids
            }

            member_serializer = GroupMemberSerializer(
                data=member_payload,
                context={"owner_id": request.user.id}
            )

            if member_serializer.is_valid():
                member_serializer.save()
            else:
                group.delete()  # rollback
                return ResponseHandler.failure(
                    message=app_messages.GROUP_MEMBER_INSERT_FAILED,
                    data=member_serializer.errors,
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            return ResponseHandler.success(
                message=app_messages.GROUP_ADDESS_SUCCESS,
                data=serializer.data,
                status_code=status.HTTP_201_CREATED
            )

        except serializers.ValidationError as ve:
            logger.error(f"API VIEW - CREATE GROUP : VALIDATION ERROR {str(ve.detail)}")
            return ResponseHandler.failure(
                message=app_messages.VALIDATION_ERROR,
                data=ve.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"API VIEW - CREATE GROUP : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=f"Unexpected error: {str(e)}"
            )

    @action(methods=['GET'], detail=True, url_path="expense-list")
    def expense_list(self, request, id=None):
        try:
            expenses = helper.fetch_user_expense(request, group_id=id)
            paginator = StandardResultsSetPagination()
            paginated_expenses = paginator.paginate_queryset(expenses, request)

            expenses_data = [
                {
                    "expense_name": e.name,
                    "expense_id": e.id,
                    "owed_expenses": helper.fetch_owed_exp_breakup(helper.fetch_expense_split(e, request)[0]),
                    "borrowed_expenses": helper.fetch_borrowed_exp_breakup(helper.fetch_expense_split(e, request)[1])
                } for e in paginated_expenses
            ]
            expenses_data = paginator.get_paginated_response(expenses_data)
            return ResponseHandler.success(
                message=app_messages.GROUP_EXPENSE_FETCHED,
                data=expenses_data
            )
        except Exception as e:
            logger.error(f"API VIEW - GROUP EXPENSE LIST : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=app_messages.GROUP_EXPENSE_NOT_FOUND,
                data=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )
