"""
Serializers for the Workflow Automation app.
"""
from rest_framework import serializers
from django.db import transaction
from .models import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowTemplate,
)


class WorkflowNodeSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowNode model."""

    class Meta:
        model = WorkflowNode
        fields = [
            'id', 'node_type', 'position_x', 'position_y',
            'config', 'label', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkflowEdgeSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowEdge model."""

    class Meta:
        model = WorkflowEdge
        fields = [
            'id', 'source_node', 'target_node', 'edge_type',
            'source_handle', 'target_handle', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WorkflowListSerializer(serializers.ModelSerializer):
    """Serializer for workflow list view (minimal fields)."""
    created_by_name = serializers.SerializerMethodField()
    node_count = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'status',
            'contacts_entered', 'contacts_active', 'contacts_completed',
            'contacts_goal_reached', 'node_count',
            'activated_at', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        name = f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return name or obj.created_by.email

    def get_node_count(self, obj):
        return obj.nodes.count()


class WorkflowSerializer(serializers.ModelSerializer):
    """Full serializer for Workflow model with nodes and edges."""
    nodes = WorkflowNodeSerializer(many=True, read_only=True)
    edges = WorkflowEdgeSerializer(many=True, read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'status',
            'canvas_data', 'goal_node_id', 'goal_description',
            'reentry', 'reentry_cooldown_days', 'entry_segment',
            'respect_quiet_hours', 'send_window_start', 'send_window_end',
            'send_weekdays', 'exit_on_goal', 'goal_rules',
            'webhook_token',
            'contacts_entered', 'contacts_active', 'contacts_completed',
            'contacts_goal_reached',
            'nodes', 'edges',
            'activated_at', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'contacts_entered', 'contacts_active',
            'contacts_completed', 'contacts_goal_reached',
            # The inbound URL is minted by the server; letting a client set it
            # would let one workflow claim another's.
            'webhook_token',
            'activated_at', 'created_by', 'created_at', 'updated_at'
        ]

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return None
        name = f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return name or obj.created_by.email


class WorkflowNodeInputSerializer(serializers.Serializer):
    """Serializer for node data in create/update requests."""
    id = serializers.CharField(required=False)  # React Flow node ID (string)
    node_type = serializers.CharField()
    position_x = serializers.FloatField(default=0)
    position_y = serializers.FloatField(default=0)
    config = serializers.JSONField(default=dict)
    label = serializers.CharField(max_length=100, required=False, allow_blank=True)


class WorkflowEdgeInputSerializer(serializers.Serializer):
    """Serializer for edge data in create/update requests."""
    id = serializers.CharField(required=False)  # React Flow edge ID
    source = serializers.CharField()  # React Flow source node ID
    target = serializers.CharField()  # React Flow target node ID
    sourceHandle = serializers.CharField(required=False, default='default')
    targetHandle = serializers.CharField(required=False, default='default')
    type = serializers.CharField(required=False, default='default')  # edge_type


def _write_edges(workflow, edges_data, node_id_map):
    """
    Replace a workflow's connections.

    Shared because create and update both do it, and because the update path
    had this nested inside its `if nodes_data is not None` block -- so a save
    that sent edges and not nodes dropped every connection on the floor
    without saying anything.

    A branch is identified by `source_handle`, which is where a switch node's
    own path names live. `edge_type` is the narrow enumerated column, so
    anything not in it is stored as 'named' rather than overflowing twenty
    characters.
    """
    known_types = dict(WorkflowEdge.EDGE_TYPE_CHOICES)

    for edge_data in edges_data:
        source_node = node_id_map.get(edge_data.get('source'))
        target_node = node_id_map.get(edge_data.get('target'))
        if not (source_node and target_node):
            continue

        branch = edge_data.get('type') or 'default'
        WorkflowEdge.objects.create(
            workflow=workflow,
            source_node=source_node,
            target_node=target_node,
            edge_type=branch if branch in known_types else 'named',
            source_handle=(edge_data.get('sourceHandle') or 'default')[:50],
            target_handle=(edge_data.get('targetHandle') or 'default')[:50],
        )


class WorkflowCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a workflow with nodes and edges."""
    nodes = WorkflowNodeInputSerializer(many=True, required=False, default=list, write_only=True)
    edges = WorkflowEdgeInputSerializer(many=True, required=False, default=list, write_only=True)

    class Meta:
        model = Workflow
        fields = [
            'name', 'description', 'canvas_data',
            'goal_node_id', 'goal_description',
            'reentry', 'reentry_cooldown_days', 'entry_segment',
            'respect_quiet_hours', 'send_window_start', 'send_window_end',
            'send_weekdays', 'exit_on_goal', 'goal_rules',
            'nodes', 'edges'
        ]

    def validate_entry_segment(self, value):
        """A workflow may only be gated by a segment from its own account."""
        if value is None:
            return value
        request = self.context.get('request')
        organization = getattr(getattr(request, 'user', None), 'organization', None)
        if organization is None or value.organization_id != organization.id:
            raise serializers.ValidationError('That segment belongs to another account.')
        return value

    def validate_send_weekdays(self, value):
        """0 is Monday and 6 is Sunday; anything else would never match."""
        if not isinstance(value, list):
            raise serializers.ValidationError('Give the days as a list.')
        cleaned = []
        for day in value:
            try:
                day = int(day)
            except (TypeError, ValueError):
                raise serializers.ValidationError('Days must be numbers from 0 to 6.')
            if not 0 <= day <= 6:
                raise serializers.ValidationError('Days must be numbers from 0 to 6.')
            cleaned.append(day)
        return sorted(set(cleaned))

    def to_representation(self, instance):
        """Return using the full WorkflowSerializer for the response."""
        return WorkflowSerializer(instance, context=self.context).data

    @transaction.atomic
    def create(self, validated_data):
        nodes_data = validated_data.pop('nodes', [])
        edges_data = validated_data.pop('edges', [])
        request = self.context.get('request')

        # Create workflow
        workflow = Workflow.objects.create(
            organization=request.user.organization,
            created_by=request.user,
            **validated_data
        )

        # Map React Flow IDs to database node objects
        node_id_map = {}

        # Create nodes
        for node_data in nodes_data:
            react_flow_id = node_data.pop('id', None)
            node = WorkflowNode.objects.create(
                workflow=workflow,
                node_type=node_data['node_type'],
                position_x=node_data.get('position_x', 0),
                position_y=node_data.get('position_y', 0),
                config=node_data.get('config', {}),
                label=node_data.get('label', ''),
            )
            if react_flow_id:
                node_id_map[react_flow_id] = node

        # Create edges using the node mapping
        _write_edges(workflow, edges_data, node_id_map)

        return workflow


class WorkflowUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a workflow with nodes and edges."""
    nodes = WorkflowNodeInputSerializer(many=True, required=False, write_only=True)
    edges = WorkflowEdgeInputSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Workflow
        fields = [
            'name', 'description', 'canvas_data',
            'goal_node_id', 'goal_description',
            'reentry', 'reentry_cooldown_days', 'entry_segment',
            'respect_quiet_hours', 'send_window_start', 'send_window_end',
            'send_weekdays', 'exit_on_goal', 'goal_rules',
            'nodes', 'edges'
        ]

    def validate_entry_segment(self, value):
        """A workflow may only be gated by a segment from its own account."""
        if value is None:
            return value
        request = self.context.get('request')
        organization = getattr(getattr(request, 'user', None), 'organization', None)
        if organization is None or value.organization_id != organization.id:
            raise serializers.ValidationError('That segment belongs to another account.')
        return value

    def validate_send_weekdays(self, value):
        """0 is Monday and 6 is Sunday; anything else would never match."""
        if not isinstance(value, list):
            raise serializers.ValidationError('Give the days as a list.')
        cleaned = []
        for day in value:
            try:
                day = int(day)
            except (TypeError, ValueError):
                raise serializers.ValidationError('Days must be numbers from 0 to 6.')
            if not 0 <= day <= 6:
                raise serializers.ValidationError('Days must be numbers from 0 to 6.')
            cleaned.append(day)
        return sorted(set(cleaned))

    def to_representation(self, instance):
        """Return using the full WorkflowSerializer for the response."""
        return WorkflowSerializer(instance, context=self.context).data

    @transaction.atomic
    def update(self, instance, validated_data):
        nodes_data = validated_data.pop('nodes', None)
        edges_data = validated_data.pop('edges', None)

        # Update workflow fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If nodes are provided, replace all nodes
        if nodes_data is not None:
            # Delete existing nodes (edges will cascade)
            instance.nodes.all().delete()

            # Map React Flow IDs to database node objects
            node_id_map = {}

            # Create new nodes
            for node_data in nodes_data:
                react_flow_id = node_data.pop('id', None)
                node = WorkflowNode.objects.create(
                    workflow=instance,
                    node_type=node_data['node_type'],
                    position_x=node_data.get('position_x', 0),
                    position_y=node_data.get('position_y', 0),
                    config=node_data.get('config', {}),
                    label=node_data.get('label', ''),
                )
                if react_flow_id:
                    node_id_map[react_flow_id] = node

            if edges_data is not None:
                _write_edges(instance, edges_data, node_id_map)

        elif edges_data is not None:
            # Connections changed but the steps did not. Deleting a connection
            # is exactly this case, and it used to be discarded because this
            # whole block sat inside `if nodes_data is not None`.
            node_id_map = {
                str(node.id): node for node in instance.nodes.all()
            }
            instance.edges.all().delete()
            _write_edges(instance, edges_data, node_id_map)

        return instance


class WorkflowExecutionStepSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowExecutionStep model."""
    node_type = serializers.CharField(source='node.node_type', read_only=True)
    node_label = serializers.CharField(source='node.label', read_only=True)

    class Meta:
        model = WorkflowExecutionStep
        fields = [
            'id', 'node', 'node_type', 'node_label',
            'status', 'started_at', 'completed_at',
            'input_data', 'output_data', 'branch_taken',
            'error_message', 'created_at'
        ]


class WorkflowExecutionListSerializer(serializers.ModelSerializer):
    """Serializer for workflow execution list view."""
    contact_email = serializers.CharField(source='contact.email', read_only=True)
    contact_name = serializers.SerializerMethodField()
    current_node_label = serializers.CharField(
        source='current_node.label', read_only=True
    )
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'contact', 'contact_email', 'contact_name',
            'status', 'current_node', 'current_node_label',
            'goal_reached', 'goal_reached_at',
            'started_at', 'completed_at', 'step_count',
            'error_message', 'retry_count'
        ]

    def get_contact_name(self, obj):
        contact = obj.contact
        if contact.first_name or contact.last_name:
            return f"{contact.first_name} {contact.last_name}".strip()
        return contact.email

    def get_step_count(self, obj):
        return obj.steps.count()


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    """Full serializer for WorkflowExecution with steps."""
    contact_email = serializers.CharField(source='contact.email', read_only=True)
    contact_name = serializers.SerializerMethodField()
    steps = WorkflowExecutionStepSerializer(many=True, read_only=True)
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)

    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'workflow', 'workflow_name',
            'contact', 'contact_email', 'contact_name',
            'status', 'current_node', 'resume_at',
            'trigger_data', 'goal_reached', 'goal_reached_at',
            'started_at', 'completed_at',
            'error_message', 'retry_count',
            'steps', 'created_at'
        ]

    def get_contact_name(self, obj):
        contact = obj.contact
        if contact.first_name or contact.last_name:
            return f"{contact.first_name} {contact.last_name}".strip()
        return contact.email


class WorkflowTemplateListSerializer(serializers.ModelSerializer):
    """Serializer for workflow template list view."""

    class Meta:
        model = WorkflowTemplate
        fields = [
            'id', 'name', 'description', 'category',
            'thumbnail_url', 'is_system', 'is_active',
            'usage_count', 'created_at'
        ]


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    """Full serializer for WorkflowTemplate model."""

    class Meta:
        model = WorkflowTemplate
        fields = [
            'id', 'name', 'description', 'category',
            'thumbnail_url', 'template_data',
            'is_system', 'is_active', 'usage_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'is_system', 'usage_count',
            'created_at', 'updated_at'
        ]


class WorkflowAnalyticsSerializer(serializers.Serializer):
    """Serializer for workflow analytics response."""
    total_entered = serializers.IntegerField()
    active = serializers.IntegerField()
    waiting = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()
    goal_reached = serializers.IntegerField()
    period_days = serializers.IntegerField()


class WorkflowValidationSerializer(serializers.Serializer):
    """Serializer for workflow validation response."""
    is_valid = serializers.BooleanField()
    errors = serializers.ListField(child=serializers.CharField())
