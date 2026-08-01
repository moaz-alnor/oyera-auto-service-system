"""Value objects used by operational reports."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class ReportDateRange:
    """Represent one inclusive reporting period."""

    start_date: date
    end_date: date

    @property
    def day_count(self) -> int:
        """Return the inclusive number of report days."""

        return (self.end_date - self.start_date).days + 1
