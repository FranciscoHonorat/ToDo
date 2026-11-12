import uuid


class MemoryRepository:
    def __init__(self):
        self.tasks = []

    def add_task(self, task):
        self.tasks.append(task)

    def get_all_tasks(self):
        return list(self.tasks)

    def find_tasks(self, status=None, limit=None, offset=0):
        matching = [task for task in self.tasks if status is None or task.status is status]
        end = None if limit is None else offset + limit
        return matching[offset:end]

    def count_tasks(self, status=None):
        return len(self.find_tasks(status))

    def get_task_by_id(self, task_id: uuid.UUID):
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None

    def update_task(self, task):
        for index, stored in enumerate(self.tasks):
            if stored.id == task.id:
                self.tasks[index] = task
                return

    def delete_task(self, task_id: uuid.UUID):
        self.tasks = [task for task in self.tasks if task.id != task_id]
