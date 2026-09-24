from .models import AuditEvent


def record_event(actor, action: str, entity, metadata=None):
    return AuditEvent.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity._meta.label,
        entity_id=str(entity.pk),
        metadata=metadata or {},
    )
