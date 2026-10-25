from django.contrib import admin

from .models import AIConfiguration, GenerationJob


@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    list_display = ['organization', 'provider', 'model', 'is_enabled', 'last_validated_at']
    list_filter = ['provider', 'is_enabled']
    search_fields = ['organization__name']
    # The key is deliberately absent: there is no reason to read it back.
    exclude = ['api_key']


@admin.register(GenerationJob)
class GenerationJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'organization', 'status', 'provider', 'model',
                    'input_tokens', 'output_tokens', 'created_at']
    list_filter = ['status', 'provider']
    search_fields = ['organization__name', 'prompt']
    readonly_fields = [f.name for f in GenerationJob._meta.fields]
