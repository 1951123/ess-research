"""Independent structural signatures for the frozen task-local graphs."""

from __future__ import annotations

from collections import Counter

from pess_ess.model import Instance

from independent_reference import maximal_matchings


def signatures(instance: Instance) -> list[dict[str, object]]:
    candidate_map = instance.candidate_map
    output = []
    for task in instance.tasks:
        local = frozenset(task.eligible_candidates)
        endpoints = {candidate_id: candidate_map[candidate_id].endpoints for candidate_id in local}
        degrees = Counter(vertex for edge in endpoints.values() for vertex in edge)
        conflict_degrees = {
            candidate_id: sum(bool(set(endpoints[candidate_id]) & set(endpoints[other])) for other in local if other != candidate_id)
            for candidate_id in local
        }
        output.append(
            {
                "task_id": task.id,
                "edges": len(local),
                "vertices": len({vertex for edge in endpoints.values() for vertex in edge}),
                "max_vertex_degree": max(degrees.values(), default=0),
                "max_conflict_degree": max(conflict_degrees.values(), default=0),
                "candidate_task_incidence": len(local),
                "maximal_matching_count": len(maximal_matchings(local, task, instance)),
            }
        )
    return output
