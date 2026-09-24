from django.contrib import admin

from .models import CandidateProposal, JobApplication, Screening

admin.site.register(JobApplication)
admin.site.register(CandidateProposal)
admin.site.register(Screening)
