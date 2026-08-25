from __future__ import annotations

from abc import ABC, abstractmethod

from campus_jobs.models import CrawlOptions, CrawlResult


class BaseAdapter(ABC):
    name = "base"
    priority = 0

    @classmethod
    @abstractmethod
    def can_handle(cls, url: str) -> bool: ...

    @abstractmethod
    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult: ...
