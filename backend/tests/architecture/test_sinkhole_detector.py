from sinkhole import find_pass_through_methods


class Example:
    def __init__(self, repository):
        self.repository = repository

    def pure_pass_through(self, task_id):
        return self.repository.get(task_id)

    def pass_through_without_return(self, task):
        self.repository.add(task)

    def documented_pass_through(self, task_id):
        """Docstrings não contam como lógica."""
        return self.repository.get(task_id)

    def with_rule(self, task_id):
        task = self.repository.get(task_id)
        if task is None:
            raise LookupError(task_id)
        return task

    def transforms_arguments(self, title):
        return self.repository.add(title.strip())

    def calls_other_collaborator(self, task_id):
        return self.clock.now(task_id)

    def _private_helper(self, task_id):
        return self.repository.get(task_id)


def test_detects_only_methods_that_just_forward_their_arguments():
    found = find_pass_through_methods(Example, collaborator="repository")

    assert found == ["documented_pass_through", "pass_through_without_return", "pure_pass_through"]
