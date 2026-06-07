from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import Doctor
from .serializers import (
    DoctorRegisterSerializer,
    DoctorLoginSerializer,
    DoctorProfileSerializer,
    ChangePasswordSerializer,
)
from .permissions import IsDoctor


class DoctorRegisterView(APIView):
    """
    POST /api/accounts/register/
    Body: {
        "username": "dr.smith",
        "email": "smith@gmail.com",
        "password": "motdepasse123",
        "password_confirm": "motdepasse123",
        "full_name": "Dr. John Smith",
        "license_number": "MED-2024-001",
        "hospital": "CHU Oran",
        "professional_email": "smith@chu-oran.dz"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DoctorRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Compte médecin créé avec succès.",
                "tokens": {
                    "refresh": str(refresh),
                    "access":  str(refresh.access_token),
                },
                "doctor": DoctorProfileSerializer(user.doctor_profile).data,
            },
            status=status.HTTP_201_CREATED,
        )


class DoctorLoginView(APIView):
    """
    POST /api/accounts/login/
    Body: {
        "username": "dr.smith",
        "password": "motdepasse123"
    }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DoctorLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user   = serializer.validated_data["user"]
        tokens = serializer.get_tokens(user)

        return Response(
            {
                "message": "Connexion réussie.",
                "tokens":  tokens,
                "doctor":  DoctorProfileSerializer(user.doctor_profile).data,
            },
            status=status.HTTP_200_OK,
        )


class DoctorLogoutView(APIView):
    """
    POST /api/accounts/logout/
    Body: { "refresh": "<refresh_token>" }
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get("refresh"))
            token.blacklist()
            return Response(
                {"message": "Déconnexion réussie."},
                status=status.HTTP_205_RESET_CONTENT,
            )
        except Exception:
            return Response(
                {"error": "Token invalide ou expiré."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DoctorProfileView(generics.RetrieveUpdateAPIView):
    serializer_class   = DoctorProfileSerializer
    permission_classes = [IsAuthenticated, IsDoctor]
    http_method_names  = ["get", "patch"]   # ← interdit PUT, autorise seulement PATCH

    def get_object(self):
        return self.request.user.doctor_profile

    def partial_update(self, request, *args, **kwargs):
        doctor = self.get_object()
        serializer = self.get_serializer(doctor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
# class ChangePasswordView(APIView):
#     """
#     POST /api/accounts/me/change-password/
#     Body: {
#         "old_password": "...",
#         "new_password": "...",
#         "confirm_password": "..."
#     }
#     """
#     permission_classes = [IsAuthenticated, IsDoctor]

#     def post(self, request):
#         serializer = ChangePasswordSerializer(
#             data=request.data, context={"request": request}
#         )
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(
#             {"message": "Mot de passe modifié avec succès. Veuillez vous reconnecter."},
#             status=status.HTTP_200_OK,
#         )

class ChangePasswordView(APIView):
    """
    POST /api/accounts/me/change-password/
    Body:
    {
        "old_password": "...",
        "new_password": "...",
        "confirm_password": "..."
    }
    """

    permission_classes = [IsAuthenticated, IsDoctor]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        # 🔥 change password
        user = serializer.save()

        # 🔥 blacklist ALL refresh tokens (logout forcé)
        try:
            # if frontend sends refresh token
            refresh_token = request.data.get("refresh")

            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            # si pas de token envoyé → on ignore
            pass

        return Response(
            {
                "message": "Mot de passe modifié. Veuillez vous reconnecter."
            },
            status=status.HTTP_200_OK,
        )
class DoctorTokenRefreshView(TokenRefreshView):
    """
    POST /api/accounts/token/refresh/
    Body: { "refresh": "<refresh_token>" }
    """
    pass