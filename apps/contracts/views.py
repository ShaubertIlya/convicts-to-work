from datetime import date
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils.dateparse import parse_date
from rest_framework import decorators, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.applications.models import JobApplication
from apps.core.identifiers import parse_uuid
from apps.core.pagination import RegistryPagination
from apps.core.permissions import NonClinicalAuthenticated

from . import services
from .models import EmploymentContract
from .serializers import EmploymentContractSerializer


def run_service(callable_, *args, **kwargs):
    try:
        return callable_(*args, **kwargs)
    except DjangoValidationError as exc:
        raise ValidationError(exc.messages) from exc


class EmploymentContractViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EmploymentContractSerializer
    permission_classes = [NonClinicalAuthenticated]
    pagination_class = RegistryPagination

    def get_queryset(self):
        queryset = EmploymentContract.objects.select_related(
            "application", "candidate", "prisoner", "organization", "organization__bank"
        ).prefetch_related("signatures__signed_by")
        if self.request.user.role == User.Role.BUSINESS_ADMIN:
            queryset = queryset.filter(organization=self.request.user.organization)
        if contract_status := self.request.query_params.get("status"):
            if contract_status not in EmploymentContract.Status.values:
                raise ValidationError({"status": "Неизвестный статус договора."})
            queryset = queryset.filter(status=contract_status)
        if number := self.request.query_params.get("number"):
            queryset = queryset.filter(number__icontains=number)
        if application_id := self.request.query_params.get("application_id"):
            try:
                queryset = queryset.filter(application_id=UUID(application_id))
            except ValueError as exc:
                raise ValidationError({"application_id": "Неверный идентификатор заявки."}) from exc
        if search := self.request.query_params.get("search", "").strip():
            queryset = queryset.filter(
                Q(number__icontains=search)
                | Q(organization__name__icontains=search)
                | Q(prisoner__full_name__icontains=search)
            )
        return queryset.order_by("-created_at", "-id")

    @decorators.action(detail=False, methods=["post"], url_path="create-from-application")
    def create_from_application(self, request):
        if request.user.role not in {User.Role.ENBEK_EXECUTOR, User.Role.ENBEK_MANAGER}:
            raise ValidationError("Только сотрудник Еңбек может создавать договоры.")
        application_id = run_service(parse_uuid, request.data.get("application_id"))
        application = JobApplication.objects.filter(id=application_id).first()
        if not application:
            raise ValidationError("Заявка не найдена.")
        starts_on = parse_date(request.data.get("starts_on", ""))
        ends_on = parse_date(request.data.get("ends_on", ""))
        if not isinstance(starts_on, date) or not isinstance(ends_on, date):
            raise ValidationError("Укажите даты в формате YYYY-MM-DD.")
        contracts = run_service(
            services.create_contracts,
            application,
            request.data.get("candidate_ids", []),
            starts_on,
            ends_on,
            request.user,
        )
        return Response(
            self.get_serializer(contracts, many=True).data, status=status.HTTP_201_CREATED
        )

    @decorators.action(detail=True, methods=["post"], url_path="start-prisoner-signature")
    def start_prisoner_signature(self, request, pk=None):
        if request.user.role not in {User.Role.ENBEK_EXECUTOR, User.Role.ENBEK_MANAGER}:
            raise ValidationError("У вашей роли нет права начинать биометрическую подпись.")
        result = run_service(
            services.start_prisoner_signature, self.get_object(), request.user,
            request.data.get("acknowledged") is True,
        )
        return Response(result, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post"], url_path="upload-document")
    def upload_document(self, request, pk=None):
        contract = run_service(
            services.upload_contract_document,
            self.get_object(), request.FILES.get("document"), request.user,
        )
        return Response(self.get_serializer(contract).data)

    @decorators.action(detail=True, methods=["post"], url_path="sign")
    def sign(self, request, pk=None):
        contract = run_service(services.button_sign, self.get_object(), request.user)
        return Response(self.get_serializer(contract).data)


class BiometryCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        base = f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/contracts"
        verification_id = request.query_params.get("verification_id", "")
        state = request.query_params.get("state", "")
        contract_number = services.biometry_contract_number(verification_id, state)
        try:
            contract = run_service(
                services.complete_biometry,
                verification_id,
                state,
                request.query_params.get("outcome", ""),
            )
        except ValidationError:
            params = {"biometry": "error"}
            if contract_number:
                params["number"] = contract_number
            return HttpResponseRedirect(f"{base}?{urlencode(params)}")
        return HttpResponseRedirect(
            f"{base}?{urlencode({'number': contract.number, 'biometry': 'success'})}"
        )
