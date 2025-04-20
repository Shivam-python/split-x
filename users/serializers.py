# serializers.py
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from users.models import User, Friends


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'mobile', 'password', 'first_name', 'last_name']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


# serializers.py


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = User.objects.filter(email=email).first()
            if user and user.check_password(password):
                if not user.is_active:
                    raise serializers.ValidationError('User account is disabled.')
                return user
            else:
                raise serializers.ValidationError('Incorrect emaiil or password.')
        else:
            raise serializers.ValidationError('Must include "email" and "password".')


class FriendSerializer(serializers.Serializer):
    user_1_id = serializers.IntegerField(required=True)
    username = serializers.CharField(required=False)
    mobile = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    def validate(self, data):
        user_1_id = data.get("user_1_id")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        mobile = data.get("mobile")
        email = data.get("email")

        # Check if friend is the same as user_1 (logged-in user)
        if mobile:
            user_2 = User.objects.filter(mobile=mobile).first()
        elif email:
            user_2 = User.objects.filter(email=email).first()
        else:
            user_2 = None

        if user_2 and user_2.id == user_1_id:
            raise serializers.ValidationError("You cannot add yourself as a friend.")

        return data

    def create(self, validated_data):
        user_1 = User.objects.get(id=validated_data['user_1_id'])
        user_2 = None
        if validated_data.get('mobile'):
            user_2 = User.objects.filter(mobile=validated_data['mobile']).first()
        elif validated_data.get('email'):
            user_2 = User.objects.filter(email=validated_data['email']).first()

        if not user_2:
            # Create a user with a dummy password
            signup_data = {
                "username": validated_data.get("username"),
                "mobile": validated_data.get("mobile"),
                "email": validated_data["email"],
                'first_name': validated_data.get("first_name"),
                'last_name': validated_data.get("last_name"),
                "password": "dummy1"
            }
            user_serializer = SignupSerializer(data=signup_data)
            user_serializer.is_valid(raise_exception=True)
            user_2 = user_serializer.save()

        # Check if the friend relation already exists
        if Friends.objects.filter(user_1=user_1, user_2=user_2).exists() or Friends.objects.filter(user_1=user_2,
                                                                                                   user_2=user_1).exists():
            raise serializers.ValidationError("Friend relation already exists.")

        # Update Friends table
        friend, created = Friends.objects.get_or_create(user_1=user_1, user_2=user_2)

        return friend


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name']
        read_only_fields = fields


class PrivateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'mobile']


class EgoUserSerializer(PrivateUserSerializer):
    class Meta:
        model = User
        fields = PrivateUserSerializer.Meta.fields


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_new_password = serializers.CharField(required=True, write_only=True)


class ForgetPasswordSerializer(serializers.Serializer):
    # todo
    token = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    confirm_new_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})


class InviteSerializer(serializers.Serializer):
    email = serializers.EmailField(label=_("Email"), allow_blank=True, required=False)
    phone = serializers.CharField(label=_("Phone"), allow_blank=True, required=False)


class FriendListSerializer(serializers.ModelSerializer):
    user_1 = PrivateUserSerializer()
    user_2 = PrivateUserSerializer()

    class Meta:
        model = Friends
        fields = ['user_1', 'user_2', 'created_at']
