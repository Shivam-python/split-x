from rest_framework import (status, viewsets, serializers as drf_serializers, permissions as drf_permissions, mixins)
from rest_framework_simplejwt.authentication import JWTAuthentication

from splitwise_app.utils.response_util import ResponseHandler
from users import serializers, models
from users.common import messages as app_messages


class FriendViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                    mixins.DestroyModelMixin, mixins.CreateModelMixin):
    """
    APIs for retrieving and managing currently logged in user's friends.

    **Permissions**:

    - _Authentication_ is required

    """
    queryset = models.Friends.objects.all()
    permission_classes = [drf_permissions.IsAuthenticated]
    authentication_classes = [JWTAuthentication]
    lookup_field = 'user_2__username'
    lookup_url_kwarg = 'username'
    serializer_class = serializers.FriendSerializer

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return serializers.FriendListSerializer
        if self.action == 'create':
            return serializers.FriendSerializer
        return drf_serializers.Serializer

    def filter_queryset(self, queryset):
        return queryset.filter(user_1=self.request.user)

    def list(self, request, *args, **kwargs):
        objects = self.get_queryset()
        serializer_class = self.get_serializer_class()
        serialized_data = serializer_class(objects, many=True)
        return ResponseHandler.success(
            message=app_messages.FRIEND_LIST_FETCHED_SUCCESSFULLY,
            data=serialized_data.data
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serialized_data = self.get_serializer(instance)
            return ResponseHandler.success(
                message=app_messages.FRIEND_DETAILS_FETCHED_SUCCESSFULLY,
                data=serialized_data.data
            )
        except Exception as e:
            return ResponseHandler.exception(
                message=app_messages.FRIEND_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND
            )

    def destroy(self, request, username=None, format=None):
        if not username:
            return ResponseHandler.failure(
                message=app_messages.INVALID_USERNAME,
                status_code=status.HTTP_406_NOT_ACCEPTABLE
            )
        friend_obj = self.queryset.filter(user_2__username=username)
        self.perform_destroy(friend_obj)
        return ResponseHandler.success(
            message=app_messages.FRIEND_REMOVED,
            status_code=status.HTTP_204_NO_CONTENT
        )

    def create(self, request, *args, **kwargs):
        try:
            request_data = request.data.copy()
            request_data['user_1_id'] = request.user.id
            serializer = self.get_serializer(data=request_data)

            serializer.is_valid(raise_exception=True)
            serializer.save()
            return ResponseHandler.success(
                message=app_messages.FRIEND_ADDED_SUCCESSFULLY,
                status_code=status.HTTP_201_CREATED
            )
        except drf_serializers.ValidationError as ve:
            return ResponseHandler.exception(
                message="Validation Failed",
                data=ve.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return ResponseHandler.exception(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
