from django.db.migrations.graph import MigrationGraph
from django.db.migrations.state import ProjectState


class ReplaceMigrationGraph(MigrationGraph):
    def make_state(self, nodes=None, at_end=True, real_apps=None):
        """
        Given a migration node or nodes, return a complete ProjectState for it.
        If at_end is False, return the state before the migration has run.
        If nodes is not provided, return the overall most current project state.
        """
        if nodes is None:
            nodes = list(self.leaf_nodes())
        if not nodes:
            return ProjectState()
        if not isinstance(nodes[0], tuple):
            nodes = [nodes]
        plan = self._generate_plan(nodes, at_end)
        project_state = ProjectState(real_apps=real_apps)
        for node in plan:
            # We have dependencies between the contrib and our migrations
            # if a node is not found, do not link / use it
            if node not in self.nodes:
                continue
            project_state = self.nodes[node].mutate_state(project_state, preserve=False)
        return project_state
