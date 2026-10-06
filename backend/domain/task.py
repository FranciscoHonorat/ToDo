
import uuid

from domain.exceptions import InvalidTitleError
from domain.status import Status


class Task:
    def __init__(self, title, description, id=None, status=Status.PENDING):
        self._validate_title(title)
        self.title = title
        self.description = description
        self.status = status
        self.id = id if id is not None else uuid.uuid4()

    @staticmethod
    def _validate_title(title):
        if not title.strip():
            raise InvalidTitleError("Title cannot be empty.")

    def complete(self):
        self.status = Status.COMPLETED

    def edit(self, title, description):
        self._validate_title(title)
        self.title = title
        self.description = description
