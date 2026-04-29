from django.contrib import admin
from .models import Result, Subject, Backlog, NBAMetric


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['subject_code', 'subject_name', 'semester', 'credits']
    search_fields = ['subject_code', 'subject_name']
    list_filter = ['semester']


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ['usn', 'subject_code', 'marks', 'sgpa', 'semester', 'category', 'is_pass']
    list_filter = ['semester', 'category', 'is_pass', 'admission_quota']
    search_fields = ['usn', 'subject_code', 'student_name']
    ordering = ['-uploaded_at']


@admin.register(Backlog)
class BacklogAdmin(admin.ModelAdmin):
    list_display = ['usn', 'subject_code', 'semester', 'marks', 'cleared']
    list_filter = ['semester', 'cleared']
    search_fields = ['usn', 'subject_code']
    actions = ['mark_cleared']

    def mark_cleared(self, request, queryset):
        queryset.update(cleared=True)
        self.message_user(request, f"{queryset.count()} backlogs marked as cleared.")
    mark_cleared.short_description = "Mark selected backlogs as cleared"


@admin.register(NBAMetric)
class NBAMetricAdmin(admin.ModelAdmin):
    list_display = ['subject_code', 'semester', 'academic_year', 'si', 'api', 'passed', 'appeared']
    list_filter = ['semester', 'academic_year']