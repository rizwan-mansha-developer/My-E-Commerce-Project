from __future__ import annotations

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(read_only=True)
    is_superuser = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_superuser",
        )
        read_only_fields = fields


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    remember_me = serializers.BooleanField(default=False, required=False)

    def validate(self, attrs: dict) -> dict:
        email = attrs["email"].strip().lower()
        password = attrs["password"]
        request = self.context.get("request")

        user = User.objects.filter(email__iexact=email).first()
        if user is not None:
            authenticated = authenticate(
                request=request,
                username=user.get_username(),
                password=password,
            )
        else:
            authenticated = authenticate(
                request=request,
                username=email,
                password=password,
            )

        if authenticated is None or not authenticated.is_active:
            raise serializers.ValidationError("Invalid email or password.")

        if not authenticated.is_superuser:
            raise serializers.ValidationError(
                "Only super admins can access the admin panel."
            )

        attrs["user"] = authenticated
        return attrs
