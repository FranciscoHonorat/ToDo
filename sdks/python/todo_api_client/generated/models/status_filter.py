from enum import StrEnum

class StatusFilter(StrEnum):
    COMPLETED = "completed"
    PENDING = "pending"

    def __str__(self) -> str:
        return str(self.value)
