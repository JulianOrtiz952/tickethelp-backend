from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Admin as AdminProxy, Technician as TechnicianProxy, Client as ClientProxy

class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('email','first_name','last_name','number','role')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('email','first_name','last_name','number','role','is_active','is_staff','is_superuser','groups','user_permissions')

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display  = ('id','email','first_name','last_name','number','role','is_active','is_staff')
    list_filter   = ('role','is_active','is_staff','is_superuser','groups')
    search_fields = ('email','first_name','last_name','name','lastName','number')
    ordering      = ('id',)

    fieldsets = (
        (None, {'fields': ('email','password')}),
        ('Información personal', {'fields': ('first_name','last_name','number')}),
        ('Rol', {'fields': ('role',)}),
        ('Permisos', {'fields': ('is_active','is_staff','is_superuser','groups','user_permissions')}),
        ('Fechas importantes', {'fields': ('last_login','date_joined')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',),
                'fields': ('email','password1','password2','first_name','last_name','number','role','is_active','is_staff')}),
    )
@admin.register(AdminProxy)
class AdminOnlyAdmin(CustomUserAdmin):
    def save_model(self, request, obj, form, change):
        obj.role = User.Role.ADMIN
        super().save_model(request, obj, form, change)

@admin.register(TechnicianProxy)
class TechOnlyAdmin(CustomUserAdmin):
    def save_model(self, request, obj, form, change):
        obj.role = User.Role.TECH
        super().save_model(request, obj, form, change)

@admin.register(ClientProxy)
class ClientOnlyAdmin(CustomUserAdmin):
    def save_model(self, request, obj, form, change):
        obj.role = User.Role.CLIENT
        super().save_model(request, obj, form, change)
