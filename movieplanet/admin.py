from django.contrib import admin
from .models import Customer
from .models import Role
from .models import Roles

# admin.site.register(Customer)

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'password', 'is_admin', 'is_active')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'status')


@admin.register(Roles)
class RolesAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assign', 'given')
