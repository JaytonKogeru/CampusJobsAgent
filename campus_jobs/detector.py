from __future__ import annotations

from .adapters import (
    ATSXAdapter,
    AshbyAdapter,
    BambuLabAdapter,
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
    TPLinkGlobalAdapter,
    VivoCampusAdapter,
    WecruitAdapter,
    WorkdayAdapter,
)

ADAPTERS = sorted(
    [
        QQDocsSourceAdapter,
        BambuLabAdapter,
        MideaCampusAdapter,
        MokaAdapter,
        VivoCampusAdapter,
        OppoAdapter,
        TPLinkGlobalAdapter,
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
