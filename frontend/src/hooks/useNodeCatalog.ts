import { useQuery } from '@tanstack/react-query';
import { workflowsApi } from '@/api/workflows';
import {
  BehaviourRuleField, NodeCatalogEntry, WorkflowNodeType,
} from '@/types/workflow';

/**
 * Everything the builder needs to know about what steps exist.
 *
 * The palette, the node config form and the rule editor all read from here.
 * They used to read a hand-written array in types/workflow.ts, which drifted
 * from the backend — four node types worked and were invisible in the builder.
 *
 * Held for an hour: the catalogue changes when the platform is deployed, not
 * while someone is building a workflow. The two hooks below share one query
 * key, so the rule editor costs no extra request.
 */
const QUERY_KEY = ['workflow-node-catalog'];
const options = {
  queryKey: QUERY_KEY,
  queryFn: workflowsApi.getNodeCatalog,
  staleTime: 60 * 60 * 1000,
  gcTime: 60 * 60 * 1000,
};

export const useNodeCatalog = () =>
  useQuery({ ...options, select: (data) => data.nodeTypes });

/** What a condition can test, beyond a contact's own properties. */
export const useRuleFields = () =>
  useQuery({ ...options, select: (data) => data.ruleFields });

/** Colour by category. A presentation choice, so it lives here, not on the server. */
export const categoryColor: Record<NodeCatalogEntry['category'], string> = {
  trigger: '#3b82f6',
  action: '#22c55e',
  condition: '#f59e0b',
};

/**
 * One node type's description, or undefined while the catalogue is loading.
 *
 * Callers must cope with undefined rather than assuming a miss means an
 * unknown node: during the first render of a saved workflow nothing has
 * arrived yet.
 */
export const useNodeType = (
  type: WorkflowNodeType | undefined,
): NodeCatalogEntry | undefined => {
  const { data } = useNodeCatalog();
  if (!type || !data) return undefined;
  return data.find((entry) => entry.type === type);
};

export type { BehaviourRuleField };
