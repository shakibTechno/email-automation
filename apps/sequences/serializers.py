"""
Serializers for the Email Sequences app.
"""
from rest_framework import serializers
from .models import EmailSequence, SequenceStep, SequenceEnrollment, SequenceStepExecution


class SequenceStepSerializer(serializers.ModelSerializer):
    template_name = serializers.SerializerMethodField()
    # Declared, and scoped to the caller's own sequences.
    #
    # It was absent from `fields` entirely, so the sequence a step belongs to
    # was read straight out of `request.data` by the viewset and looked up with
    # an unguarded .get() — a missing or unknown id raised DoesNotExist and
    # answered 500. As a real field, DRF validates it and answers 400 with a
    # message, and the queryset keeps one tenant from adding steps to another's
    # sequence.
    sequence = serializers.PrimaryKeyRelatedField(queryset=EmailSequence.objects.none())

    class Meta:
        model = SequenceStep
        fields = [
            'id', 'sequence', 'position', 'subject', 'template', 'template_name',
            'delay_days', 'delay_hours', 'total_delay_hours',
        ]
        # `position` is the server's to assign, not the client's: a step is
        # appended on create and moved by the dedicated reorder endpoint.
        read_only_fields = ['id', 'position', 'template_name', 'total_delay_hours']

        # The model's unique_together on (sequence, position) stays — it is
        # what keeps two steps off the same position. What is dropped is DRF's
        # automatic validator for it, and this is the bug that made adding a
        # second step impossible:
        #
        # `position` defaulted to 0 on every create, so the validator checked
        # (sequence, 0), found the step already there, and answered 400 before
        # perform_create could assign the real position. The first step always
        # saved and every one after it always failed.
        #
        # Safe to drop because the client no longer supplies the value: the
        # server computes it, and the database constraint is still there if it
        # ever computes a duplicate.
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        organization = getattr(getattr(request, 'user', None), 'organization', None)
        if organization is not None:
            self.fields['sequence'].queryset = EmailSequence.objects.filter(
                organization=organization, deleted_at__isnull=True,
            )

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
