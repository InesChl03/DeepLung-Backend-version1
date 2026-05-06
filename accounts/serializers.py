from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, Doctor


class DoctorRegisterSerializer(serializers.Serializer):
    # users table
    username         = serializers.CharField(max_length=150)
    email            = serializers.EmailField()
    password         = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    # doctors table
    full_name        = serializers.CharField(max_length=200)
    license_number   = serializers.CharField(max_length=50)
    hospital         = serializers.CharField(max_length=200)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already used.")
        return value

    def validate_license_number(self, value):
        if Doctor.objects.filter(license_number=value).exists():
            raise serializers.ValidationError("License number already registered.")
        return value

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        validate_password(data["password"])
        return data

    def create(self, validated_data):
        doctor_fields = {
            "full_name":      validated_data.pop("full_name"),
            "license_number": validated_data.pop("license_number"),
            "hospital":       validated_data.pop("hospital"),
        }
        validated_data.pop("password_confirm")

        user = User.objects.create_user(
            username = validated_data["username"],
            email    = validated_data["email"],
            password = validated_data["password"],
            role     = User.Role.DOCTOR,
        )
        Doctor.objects.create(user=user, **doctor_fields)
        return user


# class DoctorProfileSerializer(serializers.ModelSerializer):
#     username = serializers.CharField(source="user.username", read_only=True)
#     email    = serializers.EmailField(source="user.email",   read_only=True)

#     class Meta:
#         model  = Doctor
#         fields = [
#             "id",
#             "username",
#             "email",
#             "full_name",
#             "license_number",
#             "hospital",
#             "created_at",
#             "updated_at",
#         ]
#         read_only_fields = ["id", "created_at", "updated_at"]
class DoctorProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    email    = serializers.EmailField(source="user.email",   read_only=True)

    class Meta:
        model  = Doctor
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "license_number",
            "hospital",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "license_number",
            "created_at",
            "updated_at",
        ]
class DoctorLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        from django.contrib.auth import authenticate
        user = authenticate(username=data["username"], password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("Account disabled.")
        if not user.is_doctor():
            raise serializers.ValidationError("Not a doctor account.")
        data["user"] = user
        return data

    def get_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access":  str(refresh.access_token),
        }



class ChangePasswordSerializer(serializers.Serializer):
    old_password     = serializers.CharField(write_only=True)
    new_password     = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        validate_password(data["new_password"])
        return data

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user