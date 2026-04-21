from django.contrib.auth.hashers import make_password
from rest_framework import generics, permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from shared.cache import CacheService

from .enums import Role
from .models import User
from .services import Activator


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "role"]

    def validate(self, attrs: dict) -> dict:
        """Change the password for its hash"""

        attrs["password"] = make_password(attrs["password"])

        return attrs


class UserRegistrationPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role"]


class UserListCreateAPI(generics.ListCreateAPIView):
    http_method_names = ["get", "post"]
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return User.objects.all()

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        activator_service = Activator(email=serializer.data["email"])
        activation_key = activator_service.create_activation_key()
        activator_service.send_user_activation_email(
            activation_key=activation_key
        )

        activator_service.save_activation_information(
            internal_user_id=serializer.instance.id,
            activation_key=activation_key,
        )

        return Response(
            UserRegistrationPublicSerializer(serializer.validated_data).data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(serializer.data),
        )

    def get(self, request):
        queryset = self.get_queryset()
        serializer = UserRegistrationPublicSerializer(queryset, many=True)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class UserRetrieveAPI(generics.RetrieveUpdateDestroyAPIView):
    http_method_names = ["get", "put", "patch", "delete"]
    serializer_class = UserRegistrationPublicSerializer
    queryset = User.objects.all()
    lookup_url_kwarg = "id"

    def delete(self, request, *args, **kwargs):
        user = request.user
        if user.role != Role.ADMIN:
            raise PermissionDenied(
                "Only administrators can perform this action."
            )
        return super().delete(request, *args, **kwargs)


@api_view(http_method_names=["POST"])
@permission_classes([permissions.AllowAny])
def activate_user(request) -> Response:
    activation_key = request.data.get("activation_key")
    email = request.data.get("email")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {"message": "User does not exist"},
            status=404,
        )

    if user.is_active:
        return Response(
            {"message": "User is already activated"},
            status=200,
        )

    cache = CacheService()
    key_exists = cache.connection.exists(f"activation:{activation_key}")
    if not key_exists:
        return Response(
            {"message": "Activation key does not exist"},
            status=404,
        )

    activator_service = Activator(email=email)
    activator_service.validate_activation(key=activation_key)

    return Response(
        {"message": "Email activated successfully"},
        status=200,
    )


@api_view(http_method_names=["POST"])
@permission_classes([permissions.AllowAny])
def resend_activation_user(request) -> Response:
    email = request.data.get("email")

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {"message": "User does not exist"},
            status=404,
        )

    if user.is_active:
        return Response(
            {"message": "User is already activated"},
            status=200,
        )

    activator_service = Activator(email=email)
    activation_key = activator_service.create_activation_key()
    activator_service.send_user_activation_email(activation_key=activation_key)
    activator_service.save_activation_information(
        activation_key=activation_key, internal_user_id=user.id
    )
    return Response(
        {"message": "Activation mail resent to your email"},
        status=200,
    )
