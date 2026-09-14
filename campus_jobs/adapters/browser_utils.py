from __future__ import annotations

from typing import Any

SAFE_POPUP_TEXTS = (
    "我已阅读并同意",
    "我已阅读并理解",
    "同意并继续",
    "同意",
    "我知道了",
    "知道了",
    "确定",
    "确认",
    "关闭",
    "稍后再说",
    "暂不",
)

_BLOCKED_ACTION_WORDS = ("登录", "注册", "提交", "申请", "投递", "报名", "购买", "支付")


def dismiss_safe_popups(page: Any, *, max_clicks: int = 6) -> list[str]:
    """Dismiss obvious informational/consent overlays without triggering account actions."""
    clicked: list[str] = []
    for _ in range(max_clicks):
        action = page.evaluate(
            """
            ({labels, blocked}) => {
              const visible = (el) => {
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
              };
              const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
              const candidates = [...document.querySelectorAll('button,[role="button"],a,.el-button,.ant-btn')];
              const dialogs = [...document.querySelectorAll('[role="dialog"],.el-dialog,.ant-modal,.modal')].filter(visible);
              const ordered = [
                ...candidates.filter((el) => dialogs.some((d) => d.contains(el))),
                ...candidates,
              ];
              for (const label of labels) {
                for (const el of ordered) {
                  if (!visible(el) || el.disabled || el.getAttribute('aria-disabled') === 'true') continue;
                  const text = norm(el.innerText || el.textContent);
                  if (!text || text.length > 32) continue;
                  if (blocked.some((word) => text.includes(word))) continue;
                  if (text === label || (label.length >= 4 && text.includes(label))) {
                    el.click();
                    return text;
                  }
                }
              }
              return '';
            }
            """,
            {"labels": list(SAFE_POPUP_TEXTS), "blocked": list(_BLOCKED_ACTION_WORDS)},
        )
        if not action:
            break
        clicked.append(str(action))
        page.wait_for_timeout(350)
    return clicked
