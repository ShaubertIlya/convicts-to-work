from django.contrib import admin

from .models import Bank, OkedCode, Organization

admin.site.register(Organization)
admin.site.register(OkedCode)
admin.site.register(Bank)
