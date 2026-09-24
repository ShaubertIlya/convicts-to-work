from celery import shared_task
from django.utils import timezone

from .models import EmploymentContract


@shared_task
def expire_contracts():
    return EmploymentContract.objects.filter(
        status=EmploymentContract.Status.ACTIVE,
        ends_on__lt=timezone.localdate(),
    ).update(status=EmploymentContract.Status.EXPIRED, updated_at=timezone.now())
