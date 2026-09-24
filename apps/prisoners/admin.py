from django.contrib import admin

from .models import Prisoner, PrisonerChangeHistory, PrisonerSkill, Skill

admin.site.register(Skill)
admin.site.register(Prisoner)
admin.site.register(PrisonerSkill)
admin.site.register(PrisonerChangeHistory)
