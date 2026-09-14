from __future__ import annotations

import os
import re
import shutil


_STRONG_CONSENT_TEXTS = (
    "我已阅读并同意",
    "同意并继续",
    "接受并继续",
    "同意并进入",
    "我同意",
)

_WEAK_DIALOG_TEXTS = (
    "我知道了",
    "知道了",
    "确定",
    "确认",
    "关闭",
)

_DIALOG_SELECTORS = (
    '[role="dialog"]',
    '.el-dialog__wrapper',
    '.ant-modal-wrap',
    '.ant-modal',
    '[class*="dialog"]',
    '[class*="modal"]',
    '[class*="popup"]',
)


def chromium_launch_kwargs() -> dict[str, object]:
    """Build stable Chromium launch options for local runs and GitHub Actions."""
    kwargs: dict[str, object] = {"headless": True}
    chrome = next(
        (
            path
            for path in [
                shutil.which("google-chrome"),
                shutil.which("google-chrome-stable"),
                shutil.which("chromium"),
                shutil.which("chromium-browser"),
            ]
            if path
        ),
        None,
    )
    if chrome:
        kwargs["executable_path"] = chrome
    proxy = os.getenv("CAMPUS_JOBS_PROXY", "").strip()
    if proxy:
        kwargs["proxy"] = {"server": proxy}
    return kwargs


def _click_first_visible(locator) -> bool:
    try:
        count = min(locator.count(), 12)
    except Exception:
        return False
    for index in range(count):
        item = locator.nth(index)
        try:
            if not item.is_visible():
                continue
            item.click(timeout=1500, force=True)
            return True
        except Exception:
            continue
    return False


def dismiss_dynamic_overlays(page, *, max_rounds: int = 4) -> list[str]:
    """Dismiss common public-site consent/notice dialogs without touching login/CAPTCHA flows.

    Strong consent phrases are safe enough to match globally. Generic buttons such as
    "确定" are only clicked inside a visible dialog/modal container to avoid changing
    filters or submitting forms on the careers page itself.
    """
    clicked: list[str] = []
    for _ in range(max(1, max_rounds)):
        changed = False

        for text in _STRONG_CONSENT_TEXTS:
            try:
                locator = page.get_by_text(text, exact=True)
            except Exception:
                continue
            if _click_first_visible(locator):
                clicked.append(text)
                changed = True
                page.wait_for_timeout(250)
                break
        if changed:
            continue

        dialog = None
        for selector in _DIALOG_SELECTORS:
            try:
                candidate = page.locator(selector)
                count = min(candidate.count(), 10)
            except Exception:
                continue
            for index in range(count):
                item = candidate.nth(index)
                try:
                    if item.is_visible():
                        dialog = item
                        break
                except Exception:
                    continue
            if dialog is not None:
                break

        if dialog is not None:
            for text in _WEAK_DIALOG_TEXTS:
                try:
                    locator = dialog.get_by_text(re.compile(rf"^\s*{re.escape(text)}\s*$"))
                except Exception:
                    continue
                if _click_first_visible(locator):
                    clicked.append(text)
                    changed = True
                    page.wait_for_timeout(250)
                    break

        if not changed:
            break

    return clicked
