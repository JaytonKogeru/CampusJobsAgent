from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Job:
    id: str
    title: str
    url: str
    company: str = ""
    location: str = ""
    department: str = ""
    function: str = ""
    recruit_type: str = ""
    description: str = ""
    requirements: str = ""
    source: str = ""
    published_at: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def full_text(self) -> str:
        return "\n".join(
            part for part in [self.title, self.department, self.function, self.description, self.requirements] if part
        )

    def to_dict(self, include_extra: bool = False) -> dict[str, Any]:
        data = asdict(self)
        if not include_extra:
            data.pop("extra", None)
        return data


@dataclass(slots=True)
class CrawlOptions:
    keyword: str = ""
    scope: str = "campus"
    page_size: int = 50
    max_pages: int = 30
    max_jobs: int = 500
    include_details: bool = True
    timeout: float = 25.0
    browser_wait_ms: int = 2500


@dataclass(slots=True)
class CrawlResult:
    adapter: str
    source_url: str
    jobs: list[Job]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self, include_extra: bool = False) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "source_url": self.source_url,
            "count": len(self.jobs),
            "warnings": self.warnings,
            "jobs": [job.to_dict(include_extra=include_extra) for job in self.jobs],
        }
