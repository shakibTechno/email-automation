from django.contrib import admin
from .models import EmailSequence, SequenceStep, SequenceEnrollment, SequenceStepExecution


class SequenceStepInline(admin.TabularInline):
    model = SequenceStep
    extra = 0
    ordering = ['position']


@admin.register(EmailSequence)
class EmailSequenceAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'status', 'step_count', 'enrolled_count', 'created_at']
    list_filter = ['status', 'organization']
    search_fields = ['name']
    inlines = [SequenceStepInline]


@admin.register(SequenceEnrollment)
class SequenceEnrollmentAdmin(admin.ModelAdmin):
    list_display = ['contact', 'sequence', 'status', 'current_step_position', 'next_send_at']
    list_filter = ['status', 'sequence']
    search_fields = ['contact__email']


@admin.register(SequenceStepExecution)
class SequenceStepExecutionAdmin(admin.ModelAdmin):
    list_display = ['enrollment', 'step', 'status', 'scheduled_at', 'sent_at']
    list_filter = ['status']
