from .models import OkedCode, Organization


def build_organization_snapshot(organization: Organization) -> dict:
    """Return the legal requisites that must travel with applications and contracts."""
    oked = OkedCode.objects.filter(code=organization.oked_code).first()
    bank = organization.bank
    return {
        "name": organization.name,
        "bin": organization.bin,
        "activity_type": organization.activity_type,
        "staff_count": organization.staff_count,
        "legal_address": organization.legal_address,
        "actual_address": organization.actual_address,
        "oked": {
            "code": organization.oked_code,
            "name_ru": oked.name_ru if oked else "",
            "name_kk": oked.name_kk if oked else "",
        },
        "bank": (
            {
                "name_ru": bank.name_ru,
                "name_kk": bank.name_kk,
                "bik": bank.bic,
                "bank_code": bank.bank_code,
            }
            if bank
            else None
        ),
        "kbe": organization.kbe,
        "iik": organization.iik,
        "licenses": organization.licenses,
        "director": {
            "full_name": organization.director_full_name,
            "iin": organization.director_iin,
            "position": organization.director_position,
            "email": organization.director_email,
            "phone": organization.director_phone,
        },
    }
