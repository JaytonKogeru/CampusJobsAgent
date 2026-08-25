from __future__ import annotations

from .adapters import (
    ATSXAdapter,
    AshbyAdapter,
    GenericBrowserAdapter,
    GreenhouseAdapter,
    JobProBridgeAdapter,
    LeverAdapter,
    MokaAdapter,
    OppoAdapter,
    SmartRecruitersAdapter,
    VivoCampusAdapter,
    WecruitAdapter,
    WorkdayAdapter,
)

ADAPTERS = sorted(
    [
        MokaAdapter,
        VivoCampusAdapter,
        OppoAdapter,
        ATSXAdapter,
        WecruitAdapter,
        GreenhouseAdapter,
        LeverAdapter,
        AshbyAdapter,
        SmartRecruitersAdapter,
        WorkdayAdapter,
        JobProBridgeAdapter,
        GenericBrowserAdapter,
    ],
    key=lambda cls: cls.priority,
    reverse=True,
)


def pick_adapter(url: str):
    for cls in ADAPTERS:
        if cls.can_handle(url):
            return cls()
    return GenericBrowserAdapter()
