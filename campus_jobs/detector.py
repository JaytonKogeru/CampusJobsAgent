from __future__ import annotations

from .adapters import (
    AshbyAdapter, ATSXAdapter, GenericBrowserAdapter, GreenhouseAdapter, LeverAdapter, MokaAdapter,
    OppoAdapter, SmartRecruitersAdapter, VivoCampusAdapter, WecruitAdapter, WorkdayAdapter,
)

ADAPTERS = sorted(
    [MokaAdapter, VivoCampusAdapter, OppoAdapter, ATSXAdapter, WecruitAdapter, GreenhouseAdapter, LeverAdapter,
     AshbyAdapter, SmartRecruitersAdapter, WorkdayAdapter, GenericBrowserAdapter],
    key=lambda cls: cls.priority,
    reverse=True,
)


def pick_adapter(url: str):
    for cls in ADAPTERS:
        if cls.can_handle(url):
            return cls()
    return GenericBrowserAdapter()
