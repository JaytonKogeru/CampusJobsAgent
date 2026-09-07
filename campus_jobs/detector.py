from __future__ import annotations

from .adapters import (
    ATSXAdapter,
    AshbyAdapter,
    BeisenZhiyeAdapter,
    GenericBrowserAdapter,
    GreenhouseAdapter,
    JobProBridgeAdapter,
    LeverAdapter,
    MideaCampusAdapter,
    MokaAdapter,
    OppoAdapter,
    QQDocsSourceAdapter,
    SmartRecruitersAdapter,
    VivoCampusAdapter,
    WecruitAdapter,
    WorkdayAdapter,
)

ADAPTERS = sorted(
    [
        QQDocsSourceAdapter,
        MideaCampusAdapter,
        MokaAdapter,
        VivoCampusAdapter,
        OppoAdapter,
        ATSXAdapter,
        BeisenZhiyeAdapter,
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
