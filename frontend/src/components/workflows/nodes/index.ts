import TriggerNode from './TriggerNode';
import ActionNode from './ActionNode';
import ConditionNode from './ConditionNode';

export const nodeTypes = {
  // Triggers
  trigger_form_submission: TriggerNode,
  trigger_tag_added: TriggerNode,
  trigger_tag_removed: TriggerNode,
  trigger_contact_created: TriggerNode,
  trigger_email_opened: TriggerNode,
  trigger_email_clicked: TriggerNode,
  trigger_date_field: TriggerNode,
  // Actions
  action_send_email: ActionNode,
  action_add_tag: ActionNode,
  action_remove_tag: ActionNode,
  action_update_contact: ActionNode,
  action_wait: ActionNode,
  action_webhook: ActionNode,
  action_goal: ActionNode,
  // Conditions
  condition_if_else: ConditionNode,
};

export { TriggerNode, ActionNode, ConditionNode };
