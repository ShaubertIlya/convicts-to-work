from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import decorators, permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.models import User
from apps.core.identifiers import parse_uuid
from apps.core.pagination import RegistryPagination

from . import services
from .models import CandidateProposal, JobApplication, Screening
from .serializers import JobApplicationSerializer, ScreeningSerializer


def run_service(callable_, *args, **kwargs):
    try:
        return callable_(*args, **kwargs)
    except DjangoValidationError as exc:
        raise ValidationError(exc.messages) from exc


class JobApplicationViewSet(viewsets.ModelViewSet):
    serializer_class = JobApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RegistryPagination

    def get_queryset(self):
        queryset = JobApplication.objects.select_related(
            "organization", "organization__bank", "skill"
        ).prefetch_related("candidates__prisoner__skills", "candidates__screenings")
        role = self.request.user.role
        if role == User.Role.BUSINESS_ADMIN:
            queryset = queryset.filter(organization=self.request.user.organization)
        elif role in {User.Role.MEDIC, User.Role.PSYCHOLOGIST}:
            # Clinical staff work with screening assignments, not the business request.
            queryset = queryset.none()
        if status_filter := self.request.query_params.get("status"):
            if status_filter not in JobApplication.Status.values:
                raise ValidationError({"status": "Неизвестный статус заявки."})
            queryset = queryset.filter(status=status_filter)
        if search := self.request.query_params.get("search", "").strip():
            queryset = queryset.filter(
                Q(organization__name__icontains=search)
                | Q(skill__name_ru__icontains=search)
                | Q(workplace_address__icontains=search)
                | Q(id__icontains=search)
            )
        return queryset.order_by("-created_at", "-id")

    def perform_create(self, serializer):
        if self.request.user.role != User.Role.BUSINESS_ADMIN:
            raise ValidationError("Только МСБ может создавать заявки.")
        serializer.save()

    def perform_update(self, serializer):
        application = serializer.instance
        if (
            self.request.user.role != User.Role.BUSINESS_ADMIN
            or application.organization_id != self.request.user.organization_id
        ):
            raise ValidationError("Редактирование доступно только организации-заявителю.")
        serializer.save()

    @decorators.action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        application = self.get_object()
        if request.user.role != User.Role.BUSINESS_ADMIN:
            raise ValidationError("Только МСБ может подать заявку.")
        application = run_service(services.submit_application, application, request.user)
        return Response(self.get_serializer(application).data)

    @decorators.action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        application = self.get_object()
        if request.user.role != User.Role.BUSINESS_ADMIN:
            raise ValidationError("Только МСБ может отозвать заявку.")
        run_service(services.withdraw_application, application, request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.action(detail=True, methods=["post"])
    def propose(self, request, pk=None):
        if request.user.role != User.Role.ENBEK_EXECUTOR:
            raise ValidationError("Только исполнитель Еңбек может предложить кандидатов.")
        application = run_service(
            services.propose_candidates,
            self.get_object(),
            request.data.get("prisoner_ids", []),
            request.user,
        )
        return Response(self.get_serializer(application).data)

    @decorators.action(detail=True, methods=["post"], url_path="business-response")
    def business_response(self, request, pk=None):
        application = self.get_object()
        if request.user.role != User.Role.BUSINESS_ADMIN:
            raise ValidationError("Только МСБ может выбрать кандидатов.")
        application = run_service(
            services.business_respond,
            application,
            request.data.get("accepted_candidate_ids", []),
            request.data.get("comment", ""),
            request.user,
        )
        return Response(self.get_serializer(application).data)

    @decorators.action(detail=True, methods=["post"], url_path="enbek-decision")
    def enbek_decision(self, request, pk=None):
        if request.user.role not in {User.Role.ENBEK_MANAGER, User.Role.ENBEK_EXECUTOR}:
            raise ValidationError("У вашей роли нет права согласовать заявку.")
        approved = request.data.get("approved")
        if not isinstance(approved, bool):
            raise ValidationError({"approved": "Передайте логическое значение."})
        application = run_service(
            services.enbek_decide,
            self.get_object(),
            approved,
            request.data.get("comment", ""),
            request.user,
        )
        return Response(self.get_serializer(application).data)

    @decorators.action(detail=True, methods=["post"], url_path="send-to-screening")
    def send_to_screening(self, request, pk=None):
        if request.user.role not in {User.Role.ENBEK_EXECUTOR, User.Role.ENBEK_MANAGER}:
            raise ValidationError("Только сотрудник Еңбек направляет на обследование.")
        candidate_id = run_service(parse_uuid, request.data.get("candidate_id"))
        candidate = CandidateProposal.objects.filter(
            id=candidate_id, application=self.get_object()
        ).first()
        if not candidate:
            raise ValidationError("Кандидат не найден в заявке.")
        screening = run_service(
            services.send_to_screening, candidate, request.data.get("kind", ""), request.user
        )
        return Response(ScreeningSerializer(screening).data, status=status.HTTP_201_CREATED)


class ScreeningViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ScreeningSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = RegistryPagination

    def get_queryset(self):
        queryset = Screening.objects.select_related(
            "candidate__application",
            "candidate__application__organization",
            "candidate__application__skill",
            "candidate__prisoner",
            "reviewer",
        ).order_by("-created_at", "-id")
        role = self.request.user.role
        if role == User.Role.MEDIC:
            queryset = queryset.filter(kind=Screening.Kind.MEDICAL)
        elif role == User.Role.PSYCHOLOGIST:
            queryset = queryset.filter(kind=Screening.Kind.PSYCHOLOGICAL)
        elif role == User.Role.BUSINESS_ADMIN:
            queryset = queryset.filter(
                candidate__application__organization=self.request.user.organization
            )
        if result := self.request.query_params.get("result"):
            if result not in Screening.Result.values:
                raise ValidationError({"result": "Неизвестный результат обследования."})
            queryset = queryset.filter(result=result)
        if search := self.request.query_params.get("search", "").strip():
            queryset = queryset.filter(
                Q(candidate__prisoner__full_name__icontains=search)
                | Q(candidate__application__organization__name__icontains=search)
                | Q(candidate__application__skill__name_ru__icontains=search)
                | Q(candidate__application__workplace_address__icontains=search)
            )
        return queryset

    @decorators.action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        screening = run_service(
            services.review_screening,
            self.get_object(),
            request.data.get("result"),
            request.data.get("comment", ""),
            request.FILES.get("document"),
            request.user,
        )
        return Response(self.get_serializer(screening).data)
