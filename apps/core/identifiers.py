from uuid import UUID

from django.core.exceptions import ValidationError


def parse_uuid(value):
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValidationError("Передан некорректный идентификатор.") from exc


def parse_unique_uuid_list(values, *, allow_empty=False):
    if not isinstance(values, list):
        raise ValidationError("Передайте список идентификаторов.")
    parsed = [parse_uuid(value) for value in values]
    if (not parsed and not allow_empty) or len(parsed) != len(set(parsed)):
        raise ValidationError("Передайте список уникальных идентификаторов.")
    return parsed
