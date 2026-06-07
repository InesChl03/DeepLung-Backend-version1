from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Doctor


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ["username", "email", "role", "is_active"]
    list_filter   = ["role", "is_active"]
    search_fields = ["username", "email"]
    ordering      = ["-date_joined"]
    fieldsets     = UserAdmin.fieldsets + (
        ("Role", {"fields": ("role",)}),
    )


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display  = ["full_name", "license_number", "hospital", "get_email"]
    search_fields = ["full_name", "license_number"]
    ordering      = ["-created_at"]

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = "Email professionnel"