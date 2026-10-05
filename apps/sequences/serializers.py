"""
Serializers for the Email Sequences app.
"""
from rest_framework import serializers
from .models import EmailSequence, SequenceStep, SequenceEnrollment, SequenceStepExecution


class SequenceStepSerializer(serializers.ModelSerializer):
    template_name = serializers.SerializerMethodField()

    class Meta:
        model = SequenceStep
        fields = [
            'id', 'position', 'subject', 'template', 'template_name',
            'delay_days', 'delay_hours', 'total_delay_hours',
        ]
        read_only_fields = ['id', 'template_name', 'total_delay_hours']

    def get_template_name(self, obj):
        return obj.template.name if obj.template else None


class EmailSequenceListSerializer(serializers.ModelSerializer):
    step_count = serializers.IntegerField(read_only=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    completed_count = serializers.IntegerField(read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EmailSequence
        fields = [
            'id', 'name', 'description', 'status',
            'sender_name', 'sender_email',
            'step_count', 'enrolled_count', 'completed_count',
            'allow_reenrollment', 'created_by_name',
            'created_at', 'updated_at',
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.full_name or obj.created_by.email
        return None


class EmailSequenceSerializer(EmailSequenceListSerializer):
    steps = SequenceStepSerializer(many=True, read_only=True)

    class Meta(EmailSequenceListSerializer.Meta):
        fields = EmailSequenceListSerializer.Meta.fields + ['steps', 'reply_to_email']


class EmailSequenceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSequence
        fields = [
            'name', 'description', 'status',
            'sender_name', 'sender_email', 'reply_to_email',
            'allow_reenrollment',
        ]


class SequenceEnrollmentSerializer(serializers.ModelSerializer):
    contact_email = serializers.SerializerMethodField()
    contact_name = serializers.SerializerMethodField()
    sequence_name = serializers.SerializerMethodField()

    class Meta:
        model = SequenceEnrollment
        fields = [
            'id', 'sequence', 'sequence_name', 'contact', 'contact_email', 'contact_name',
            'status', 'current_step_position', 'enrolled_at', 'completed_at', 'next_send_at',
        ]
        read_only_fields = ['id', 'enrolled_at', 'completed_at', 'next_send_at', 'current_step_position']

    def get_contact_email(self, obj):
        return obj.contact.email

    def get_contact_name(self, obj):
        return obj.contact.full_name

    def get_sequence_name(self, obj):
        return obj.sequence.name


class SequenceStepExecutionSerializer(serializers.ModelSerializer):
    step_subject = serializers.SerializerMethodField()
    step_position = serializers.SerializerMethodField()

    class Meta:
        model = SequenceStepExecution
        fields = [
            'id', 'step', 'step_subject', 'step_position',
            'status', 'scheduled_at', 'sent_at', 'error_message',
            'opened_at', 'clicked_at',
        ]

    def get_step_subject(self, obj):
        return obj.step.subject

    def get_step_position(self, obj):
        return obj.step.position
