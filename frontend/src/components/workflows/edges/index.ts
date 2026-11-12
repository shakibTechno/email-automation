import { EdgeTypes } from 'reactflow';
import DeletableEdge from './DeletableEdge';

/**
 * One edge type for the whole canvas.
 *
 * Registered as the default so every connection — existing ones loaded from
 * the server and new ones drawn by hand — gets the same delete affordance.
 */
export const edgeTypes: EdgeTypes = {
  deletable: DeletableEdge,
};

export const EDGE_TYPE = 'deletable';

export { DeletableEdge };
