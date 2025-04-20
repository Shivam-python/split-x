import logging

from django.core.mail import send_mail
from django.conf import settings

from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import (status, viewsets, serializers as drf_serializers, permissions as drf_permissions, mixins)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication

from splitwise_app.utils.response_util import ResponseHandler
from users import serializers, models, permissions
from users.common import messages as app_messages

logger = logging.getLogger('users')


class UserViewSet(
    viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, mixins.ListModelMixin
):
    """
    API for user information management and retrieval

    * **login** [`/user/login/|POST`]: obtain a valid authentication token by sending valid credentials url
    * **logout** [`/user/logout/|POST`]: invalidate currently owned authentication token
    * **retrieve** [`/user/<username>/|GET`]: obtain user information (by looking up username)
    * **list** [`/user/|GET`]: get the list of all users
    * **update** [`/user/me/|PUT`]: update ego user's information (excluding the password)
    * **retrieve** [`/user/me/|GET`]: obtain current user information
    * **change_password** [`/user/change_password|POST`]: update user password (old password is required)
    * **invite** [`/user/invite|POST`]: invite external users
    """

    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    authentication_classes = [JWTAuthentication]
    serializer_class = serializers.EgoUserSerializer
    queryset = models.User.objects.all()

    def get_view_name(self):
        return getattr(self, 'name', 'User') or 'User'

    def get_view_name(self):
        return getattr(self, 'name', 'User') or 'User'

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.SignupSerializer
        if self.action in ['retrieve', 'update', 'me', 'list']:
            if self.request.user.is_staff or (
                    'username' in self.request.parser_context['kwargs'] and
                    self.request.user.username == self.request.parser_context['kwargs']['username']):
                return serializers.EgoUserSerializer
            else:
                return serializers.UserSerializer
        elif self.action == 'change_password':
            return serializers.ChangePasswordSerializer
        elif self.action == 'login':
            return serializers.LoginSerializer
        elif self.action == 'logout':
            return drf_serializers.Serializer
        elif self.action == 'friends':
            if self.request.method == 'GET':
                return serializers.FriendSerializer
            else:
                return drf_serializers.Serializer
        elif self.action == 'invite':
            return serializers.InviteSerializer
        return serializers.UserSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ['create', 'login', 'refresh-token']:
            permission_list = [drf_permissions.AllowAny]
        elif self.action in ['update', 'change_password', 'logout', 'me']:
            permission_list = [permissions.IsSelfOrAdmin, drf_permissions.IsAuthenticated]
        elif self.action in ['retrieve', 'list', 'invite']:
            permission_list = [drf_permissions.IsAuthenticated]
        else:
            permission_list = [drf_permissions.AllowAny]
        return [permission() for permission in permission_list]

    @action(methods=['GET', 'PUT'], detail=False)
    def me(self, request):
        """
        Retrieve and change the current user's account information.

        **Permissions**:

        * _Authentication_ is required
        * API only available to _Owner_ of the account
        """
        if request.method == 'GET':
            self.kwargs['id'] = request.user.id
            return self.retrieve(request)

        elif request.method == 'PUT':
            self.kwargs['id'] = request.user.id
            return self.update(request)
        return ResponseHandler.failure(
            message=app_messages.PROFILE_NOT_FOUNF,
            status_code=status.HTTP_404_NOT_FOUND
        )

    @action(methods=['POST'], detail=False, )
    def change_password(self, request, format=None):
        """
        Change user's passcode API by providing the old password.

        **Permissions**:

        * _Authentication_ is required
        * API only available to _Admins_ or the _Owner_ of the account
        """
        user = request.user
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not user.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

            # confirm the new passwords match
            new_password = serializer.data.get("new_password")
            confirm_new_password = serializer.data.get("confirm_new_password")
            if new_password != confirm_new_password:
                return Response({"new_password": ["New passwords must match"]}, status=status.HTTP_400_BAD_REQUEST)

            # set_password also hashes the password that the user will get
            user.set_password(serializer.data.get("new_password"))
            user.object.save()
            return Response({"response": "successfully changed password"}, status=status.HTTP_200_OK)

        return ResponseHandler.failure(
            message="Profile data not found",
            data=serializer.errors,
            status_code=status.HTTP_404_NOT_FOUND
        )

    @action(methods=['POST'], detail=False, )
    def login(self, request, format=None):
        """
        Obtain an authentication token by providing valid credentials.
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data
            if user.is_active:  # todo: handle account activation
                refresh = RefreshToken.for_user(user)
                return ResponseHandler.success(
                    message=app_messages.LOGIN_SUCCESS,
                    data={
                        'access_token': str(refresh.access_token),
                        'refresh_token': str(refresh),
                    }
                )
            return ResponseHandler.failure(
                message=app_messages.LOGIN_FAILED,
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"API VIEW - LOGIN : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=app_messages.LOGIN_FAILED,
                data=None,
            )

    @action(methods=['POST'], detail=False, url_path='refresh-token')
    def refresh_token(self, request, format=None):
        """
        Obtain an authentication token by providing valid credentials.
        """
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            return ResponseHandler.success(
                message=app_messages.TOKEN_REFRESHED,
                data={
                    'access_token': str(token.access_token),
                    'refresh_token': str(token),
                }
            )
        except Exception as e:
            logger.error(f"API VIEW - REFRESH TOKEN : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=app_messages.TOKEN_REFRESH_FAILED,
                data=None,
            )

    @action(methods=['POST'], detail=False, )
    def logout(self, request, format=None):
        """
         Invalidate the currently owned authentication token.

         **Permissions** :

         * _Authentication_ is required
        """
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return ResponseHandler.success(
                message=app_messages.LOG_OUT_SUCCESS,
                status_code=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            logger.error(f"API VIEW - LOGOUT : ERROR {str(e)}")
            return ResponseHandler.success(
                message=app_messages.LOGOUT_FAILED + " " + str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(methods=['POST'], detail=False, )
    def reset_password(self, request, format=None):
        """
        Change the password for every user with the possession of valid ForgetTokens
        """
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(methods=['POST'], detail=False, )
    def invite(self, request, format=None):
        """
        Invite external users

        Permissions:

        * _Authentication_ is required
        """
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            if 'email' in serializer.validated_data and serializer.validated_data['email']:
                send_mail(subject=app_messages.INVITE_SUBJECT,
                          message=f'''Howdy fellow human!
                          Your friend {request.user.first_name.capitalize() if request.user.first_name else request.user.username} has invited you to
                           join the Split-X platform.''',
                          html_message=f'''Howdy fellow human!<br> Your friend <strong>
                            {request.user.first_name.capitalize() if request.user.first_name else request.user.username}
                          </strong> has invited you to join the <a href="#">Split-X</a> platform.''',
                          from_email=settings.EMAIL_HOST_USER,
                          recipient_list=[serializer.validated_data['email']],
                          fail_silently=True)

            # todo add phone api as well
            return ResponseHandler.success(
                message=app_messages.INVITE_SENT,
                status_code=status.HTTP_202_ACCEPTED
            )
        except Exception as e:
            logger.error(f"API VIEW - INVITE USER : ERROR {str(e)}")
            return ResponseHandler.exception(
                message=app_messages.INVITE_FAILED,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(methods=['POST'], detail=False, )
    def forget_password(self, request, format=None):
        """
        Request for acquirement of a ForgetToken
        """
        # todo email
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(methods=['POST'], detail=False, )
    def validate_account(self, request, format=None):
        """
        Activate account of any user with the possession of a valid activation token
        """
        return Response(status=status.HTTP_202_ACCEPTED)

    @action(methods=['POST'], detail=False, )
    def resend_validation(self, request, format=None):
        """
        Activate account of any user with the possession of a valid activation token
        """
        # todo email
        return Response(status=status.HTTP_202_ACCEPTED)
