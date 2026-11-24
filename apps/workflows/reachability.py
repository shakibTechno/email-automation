"""
Whether every node on the canvas can actually be reached.

A workflow runs by walking edges out of the node it is on. A node with nothing
leading into it is never visited, and the run simply finishes — status
`completed`, no error, nothing in the log. That is how an active workflow came
to send its intro email, add its tag, and stop one edge short of the condition
that led to its goal, while the detail page reported both runs as completed.

So the graph is checked where it is saved and read, and what it finds is
reported with the workflow. Nothing is blocked: half-built workflows are the
normal state of a canvas someone is still working on, and a builder that
refuses to save is worse than one that tells you what is dangling.
"""
from __future__ import annotations

from apps.workflows import catalog

GOAL_TYPE = 'action_goal'


def _label(node):
    """What to call a node in a message: its own name, else its type's."""
    if node.label:
        return node.label
    spec = catalog.spec_for(node.node_type)
    return spec.label if spec else node.node_type


def _graph(workflow):
    """Nodes by id and an adjacency map, from what is already loaded."""
    nodes = {str(node.id): node for node in workflow.nodes.all()}
    out = {node_id: [] for node_id in nodes}
    for edge in workflow.edges.all():
        source = str(edge.source_node_id)
        target = str(edge.target_node_id)
        if source in out and target in nodes:
            out[source].append(target)
    return nodes, out


def reachable_ids(workflow):
    """Every node id reachable from any trigger, the triggers included."""
    nodes, out = _graph(workflow)

    seen = set()
    queue = [
        node_id for node_id, node in nodes.items()
        if node.node_type in catalog.TRIGGER_TYPES
    ]
    seen.update(queue)

    while queue:
        current = queue.pop()
        for target in out.get(current, ()):
            if target not in seen:
                seen.add(target)
                queue.append(target)

    return seen


def problems(workflow):
    """
    What is wrong with the shape of this workflow, as plain data.

    A list so the builder can show every issue at once, each with the nodes it
    concerns, so the canvas can point at them.
    """
    nodes, _ = _graph(workflow)
    if not nodes:
        return []

    found = []

    triggers = [n for n in nodes.values() if n.node_type in catalog.TRIGGER_TYPES]
    if not triggers:
        return [{
            'code': 'no_trigger',
            'message': 'This workflow has no trigger, so nothing can enter it.',
            'node_ids': [],
        }]

    reached = reachable_ids(workflow)

    stranded = [
        node for node_id, node in nodes.items() if node_id not in reached
    ]
    if stranded:
        labels = ', '.join(_label(node) for node in stranded[:4])
        count = len(stranded)
        found.append({
            'code': 'unreachable',
            'message': (
                f'{count} step{"" if count == 1 else "s"} '
                f'{"is" if count == 1 else "are"} not connected to the trigger '
                f'and will never run: {labels}'
                + (f' and {count - 4} more' if count > 4 else '')
                + '.'
            ),
            'node_ids': [str(node.id) for node in stranded],
        })

    goals = [n for n in nodes.values() if n.node_type == GOAL_TYPE]
    unreached_goals = [g for g in goals if str(g.id) not in reached]
    if goals and len(unreached_goals) == len(goals):
        found.append({
            'code': 'goal_unreachable',
            'message': (
                'No path leads to the goal, so no contact can ever reach it.'
            ),
            'node_ids': [str(g.id) for g in unreached_goals],
        })

    return found
