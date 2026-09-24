import random
from datetime import date
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw

from apps.accounts.models import User
from apps.organizations.models import OkedCode, Organization
from apps.prisoners.models import Prisoner, PrisonerChangeHistory, PrisonerSkill, Skill


class Command(BaseCommand):
    help = "Создаёт идемпотентные вымышленные данные для локальной разработки."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="Dev-password-123")

    def handle(self, *args, **options):
        password = options["password"]
        enbek, _ = Organization.objects.update_or_create(
            bin="000000000001",
            defaults={
                "name": "РГП Еңбек (тест)",
                "kind": Organization.Kind.ENBEK,
                "activity_type": "Организация трудовой занятости",
                "staff_count": 100,
                "legal_address": "Тестовый адрес",
                "actual_address": "Тестовый адрес",
                "actual_address_same": True,
                "oked_code": "84110",
                "bank_details": "Тестовые банковские реквизиты",
                "licenses": "",
                "director_full_name": "Тестовый руководитель Еңбек",
                "director_iin": "000000000001",
                "director_position": "Руководитель",
                "director_email": "director@enbek.example.test",
                "director_phone": "+70000000001",
            },
        )
        roles = {
            "admin@enbek.example.test": (User.Role.ENBEK_ADMIN, "Тестовый администратор"),
            "manager@enbek.example.test": (User.Role.ENBEK_MANAGER, "Тестовый руководитель"),
            "executor@enbek.example.test": (User.Role.ENBEK_EXECUTOR, "Тестовый исполнитель"),
            "medic@enbek.example.test": (User.Role.MEDIC, "Тестовый медик"),
            "psychologist@enbek.example.test": (
                User.Role.PSYCHOLOGIST,
                "Тестовый психолог",
            ),
        }
        for email, (role, full_name) in roles.items():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "role": role,
                    "full_name": full_name,
                    "organization": enbek,
                },
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])

        oked_rows = [
            ("41201", "Строительство жилых зданий", "Тұрғын үй ғимараттарының құрылысы"),
            ("43219", "Прочие электромонтажные работы", "Өзге де электр монтаждау жұмыстары"),
            ("14120", "Производство спецодежды", "Арнайы киім өндіру"),
        ]
        for code, name_ru, name_kk in oked_rows:
            OkedCode.objects.update_or_create(
                code=code, defaults={"name_ru": name_ru, "name_kk": name_kk}
            )

        skill_rows = [
            ("Электрик", "Электрик"),
            ("Сварщик", "Дәнекерлеуші"),
            ("Швея", "Тігінші"),
            ("Кочегар", "От жағушы"),
            ("Разнорабочий", "Әр түрлі жұмысшы"),
            ("Каменщик", "Тас қалаушы"),
            ("Плотник", "Ағаш ұстасы"),
            ("Сантехник", "Сантехник"),
            ("Повар", "Аспаз"),
            ("Водитель", "Жүргізуші"),
        ]
        skills = []
        for name_ru, name_kk in skill_rows:
            skill, _ = Skill.objects.update_or_create(
                name_ru=name_ru, defaults={"name_kk": name_kk}
            )
            skills.append(skill)

        full_names = [
            "Тестовый Ахметов Арман Серикович",
            "Тестовый Беков Данияр Маратович",
            "Тестовый Васильев Илья Олегович",
            "Тестовый Габдуллин Руслан Азатович",
            "Тестовый Досанов Нурлан Ерланович",
            "Тестовый Ермеков Алибек Талгатович",
            "Тестовый Жумабаев Марат Канатович",
            "Тестовый Ибраев Тимур Болатович",
            "Тестовый Касымов Олжас Ринатович",
            "Тестовый Ли Александр Денисович",
            "Тестовый Мусин Айдар Саматович",
            "Тестовый Нургалиев Берик Аскарович",
            "Тестовый Омаров Даурен Жанатович",
            "Тестовый Петров Сергей Андреевич",
            "Тестовый Рахимов Азамат Муратович",
            "Тестовый Садыков Ерасыл Бауыржанович",
            "Тестовый Тлеубаев Максат Серикович",
            "Тестовый Усенов Артур Рашидович",
            "Тестовый Фёдоров Павел Игоревич",
            "Тестовый Хасенов Санжар Ермекович",
        ]
        educations = [
            "Среднее общее",
            "Техническое и профессиональное",
            "Среднее специальное",
            "Высшее",
        ]
        qualifications = [
            "Электромонтёр 3 разряда",
            "Сварщик ручной дуговой сварки",
            "Швея 3 разряда",
            "Оператор котельной",
            "Рабочий строительной бригады",
            "Каменщик 4 разряда",
            "Столяр-плотник",
            "Слесарь-сантехник",
            "Повар 3 разряда",
            "Водитель категории B, C",
        ]
        experience_rows = [
            "Монтаж и обслуживание электрооборудования",
            "Сварочные работы на производстве",
            "Пошив спецодежды и ремонт изделий",
            "Эксплуатация твердотопливных котлов",
            "Общестроительные и погрузочные работы",
            "Кладка кирпича и отделочные работы",
            "Изготовление деревянных конструкций",
            "Монтаж и ремонт инженерных сетей",
            "Работа на производственной кухне",
            "Перевозка грузов и обслуживание автомобиля",
        ]
        health_rows = [
            "Практически здоров, трудоспособен",
            "Состояние удовлетворительное",
            "Хроническое заболевание в ремиссии",
        ]
        employment_rows = [
            "Не трудоустроен",
            "Хозяйственный отряд учреждения",
            "Швейный участок учреждения",
            "Ремонтная мастерская учреждения",
            "Производственный участок учреждения",
        ]
        rng = random.Random(20260922)
        for index, full_name in enumerate(full_names, start=1):
            iin = f"900101{index:06d}"
            skill_index = (index - 1) % len(skills)
            health_status = health_rows[(index - 1) % len(health_rows)]
            current_employment = employment_rows[(index - 1) % len(employment_rows)]
            prisoner, created = Prisoner.objects.update_or_create(
                iin=iin,
                defaults={
                    "full_name": full_name,
                    "birth_date": date(1980 + index, (index % 12) + 1, (index % 27) + 1),
                    "rating": rng.randint(1, 5),
                    "is_available": index % 5 != 0,
                    "work_capacity": (
                        Prisoner.WorkCapacity.UNABLE
                        if index in {6, 11}
                        else Prisoner.WorkCapacity.CAPABLE
                    ),
                    "criminal_article": f"ст. {188 + (index % 6)} УК РК (тестовые данные)",
                    "sentence_term": f"{2 + index % 6} лет",
                    "sentence_start": date(2022 + index % 3, (index % 12) + 1, 1),
                    "sentence_end": date(2027 + index % 4, (index % 12) + 1, 1),
                    "education": educations[(index - 1) % len(educations)],
                    "qualification": qualifications[skill_index],
                    "pre_prison_experience": experience_rows[skill_index],
                    "pre_prison_experience_years": 1 + index % 12,
                    "penitentiary_education": (
                        f"Курс «{skills[skill_index].name_ru}», учебный центр УИС"
                        if index % 3
                        else "Не проходил обучение в УИС"
                    ),
                    "health_status": health_status,
                    "disability_status": (
                        Prisoner.DisabilityStatus.GROUP_3
                        if index in {7, 17}
                        else Prisoner.DisabilityStatus.NONE
                    ),
                    "medical_restrictions": (
                        "Исключить подъём тяжестей свыше 10 кг" if index % 6 == 0 else ""
                    ),
                    "current_employment": current_employment,
                    "total_work_experience_years": 2 + index % 16,
                    "pension_status": (
                        Prisoner.PensionStatus.DISABILITY
                        if index in {7, 17}
                        else Prisoner.PensionStatus.NONE
                    ),
                    "disciplinary_restrictions": (
                        "Ограничение на работы вне охраняемой территории" if index % 7 == 0 else ""
                    ),
                    "safety_briefing_info": (
                        f"Первичный инструктаж пройден 15.{(index % 9) + 1:02d}.2026"
                    ),
                },
            )
            reference_name = f"prisoners/reference/public-portrait-{index:02d}.jpg"
            local_reference = Path(settings.MEDIA_ROOT) / reference_name
            current_name = Path(prisoner.photo.name).name if prisoner.photo else ""
            demo_photo = current_name.startswith(
                ("public-portrait-", "test-prisoner-", "demo-placeholder-")
            )
            if (created or not prisoner.photo or demo_photo) and local_reference.is_file():
                if prisoner.photo.name != reference_name:
                    prisoner.photo.name = reference_name
                    prisoner.save(update_fields=["photo"])
            elif not prisoner.photo or (
                demo_photo and not prisoner.photo.storage.exists(prisoner.photo.name)
            ):
                prisoner.photo.save(
                    f"demo-placeholder-{index:02d}.jpg",
                    ContentFile(self._placeholder_photo(index)),
                    save=True,
                )
            PrisonerSkill.objects.filter(prisoner=prisoner).delete()
            extra_skills = rng.sample(
                [item for item in skills if item != skills[skill_index]],
                k=index % 3,
            )
            for skill in [skills[skill_index], *extra_skills]:
                PrisonerSkill.objects.get_or_create(prisoner=prisoner, skill=skill)
            history_rows = [
                (
                    PrisonerChangeHistory.ChangeType.QUALIFICATION,
                    "Без подтверждённого разряда",
                    prisoner.qualification,
                    "Результат обучения и аттестации",
                ),
                (
                    PrisonerChangeHistory.ChangeType.HEALTH,
                    "Первичный осмотр",
                    prisoner.health_status,
                    "Плановое медицинское обследование",
                ),
                (
                    PrisonerChangeHistory.ChangeType.EMPLOYMENT,
                    "Не трудоустроен",
                    prisoner.current_employment,
                    "Актуализация занятости",
                ),
            ]
            for offset, (change_type, previous, new, note) in enumerate(history_rows):
                PrisonerChangeHistory.objects.update_or_create(
                    prisoner=prisoner,
                    change_type=change_type,
                    effective_date=date(2026, 1 + offset * 2, min(index, 28)),
                    defaults={
                        "previous_value": previous,
                        "new_value": new,
                        "note": note,
                    },
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Тестовые данные готовы. Карточки вымышлены; фото берутся "
                "только из локальной media-папки."
            )
        )

    @staticmethod
    def _placeholder_photo(index):
        image = Image.new("RGB", (480, 640), (35 + index * 7, 82, 72))
        draw = ImageDraw.Draw(image)
        draw.ellipse((140, 140, 340, 340), fill=(220, 220, 210))
        draw.rectangle((100, 360, 380, 610), fill=(190, 195, 185))
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=88)
        return buffer.getvalue()
