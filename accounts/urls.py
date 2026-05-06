# from django.urls import path 
# from .views import (
#     DoctorRegisterView,
#     DoctorLoginView,
#     DoctorLogoutView,
#     DoctorProfileView,
#     DoctorUserUpdateView,
#     ChangePasswordView,
#     DoctorTokenRefreshView,
# )

# app_name = "accounts"

# urlpatterns = [
#     # Auth
#     path("register/",         DoctorRegisterView.as_view(),     name="doctor-register"),
#     path("login/",            DoctorLoginView.as_view(),        name="doctor-login"),
#     path("logout/",           DoctorLogoutView.as_view(),       name="doctor-logout"),
#     path("token/refresh/",    DoctorTokenRefreshView.as_view(), name="token-refresh"),

#     # Profile
#     path("me/",               DoctorProfileView.as_view(),      name="doctor-profile"),
#     path("me/user/",          DoctorUserUpdateView.as_view(),   name="doctor-user-update"),
#     path("me/change-password/", ChangePasswordView.as_view(),   name="doctor-change-password"),
# ]

# # ─────────────────────────────────────────────
# # In your root urls.py add:
# #
# #   path("api/accounts/", include("accounts.urls")),
# # ─────────────────────────────────────────────
from django.urls import path
from .views import (
    DoctorRegisterView,
    DoctorLoginView,
    DoctorLogoutView,
    DoctorProfileView,
    ChangePasswordView,
    DoctorTokenRefreshView,
)

app_name = "accounts"

urlpatterns = [
    # Auth
    path("register/", DoctorRegisterView.as_view()),
    path("login/", DoctorLoginView.as_view()),
    path("logout/", DoctorLogoutView.as_view()),
    path("token/refresh/", DoctorTokenRefreshView.as_view()),

    # Profile
    path("me/", DoctorProfileView.as_view()),
    path("me/change-password/", ChangePasswordView.as_view()),
]