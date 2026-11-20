from enum import StrEnum

class Status(StrEnum):
    COMPLETED = "COMPLETED"
    PENDING = "PENDING"

    def __str__(self) -> str:
        return str(self.value)
