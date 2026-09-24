from django.contrib import admin

from .models import BiometricSignatureAttempt, ContractSignature, EmploymentContract

admin.site.register(EmploymentContract)
admin.site.register(ContractSignature)
admin.site.register(BiometricSignatureAttempt)
