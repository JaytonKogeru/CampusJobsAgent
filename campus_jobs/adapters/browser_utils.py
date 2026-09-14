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
    """Dismiss obvious informational/consent overlays without triggering account actions.

    Some recruiting portals render the acknowledgement as a ``div``/``span`` or
    checkbox label instead of a semantic button. We therefore match exact safe
    labels across visible leaf elements, but never click text that contains an
    application/account action word.
    """
    clicked: list[str] = []
    attempted: list[str] = []
    for _ in range(max_clicks):
        action = page.evaluate(
            r"""
            ({labels, blocked, attempted}) => {
              const visible = (el) => {
                if (!el) return false;
                const style = window.getComputedStyle(el);
                const rect = el.getBoundingClientRect();
                return style.visibility !== 'hidden'
                  && style.display !== 'none'
                  && Number(style.opacity || 1) !== 0
                  && rect.width > 0
                  && rect.height > 0;
              };
              const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
              const overlaySelector = [
                '[role="dialog"]', '.el-dialog', '.ant-modal', '.modal',
                '[class*="dialog"]', '[class*="modal"]', '[class*="popup"]',
                '[class*="notice"]', '[class*="tips"]', '[class*="mask"]'
              ].join(',');
              const overlays = [...document.querySelectorAll(overlaySelector)].filter(visible);
              const inOverlay = (el) => overlays.some((overlay) => overlay.contains(el));
              const controls = [
                ...document.querySelectorAll(
                  'button,[role="button"],a,label,input[type="checkbox"],.el-button,.ant-btn,span,div'
                )
              ].filter(visible);

              const candidates = [];
              for (const el of controls) {
                if (el.matches('input[type="checkbox"]')) {
                  if (el.checked) continue;
                  const parent = el.closest('label') || el.parentElement;
                  const text = norm(parent && (parent.innerText || parent.textContent));
                  if (!labels.some((label) => text === label || text.startsWith(label))) continue;
                  if (blocked.some((word) => text.includes(word))) continue;
                  candidates.push({el, text, key: `checkbox:${text}`, rank: inOverlay(el) ? 0 : 4});
                  continue;
                }

                const text = norm(el.innerText || el.textContent);
                if (!text || text.length > 40) continue;
                if (blocked.some((word) => text.includes(word))) continue;
                const labelIndex = labels.findIndex(
                  (label) => text === label || (label.length >= 4 && text.startsWith(label) && text.length <= label.length + 12)
                );
                if (labelIndex < 0) continue;
                if (el.disabled || el.getAttribute('aria-disabled') === 'true') continue;

                const tag = el.tagName.toLowerCase();
                const semantic = tag === 'button' || tag === 'a' || tag === 'label'
                  || el.getAttribute('role') === 'button'
                  || /(^|\s)(el-button|ant-btn)(\s|$)/.test(el.className || '');
                const leaf = ![...el.children].some((child) => visible(child) && norm(child.innerText || child.textContent) === text);
                if (!semantic && !leaf) continue;
                const key = `${tag}:${text}`;
                let rank = labelIndex * 10;
                if (inOverlay(el)) rank -= 6;
                if (semantic) rank -= 3;
                if (leaf) rank -= 1;
                candidates.push({el, text, key, rank});
              }

              candidates.sort((a, b) => a.rank - b.rank);
              const pick = candidates.find((item) => !attempted.includes(item.key));
              if (!pick) return '';
              pick.el.click();
              return pick.key;
            }
            """,
            {
                "labels": list(SAFE_POPUP_TEXTS),
                "blocked": list(_BLOCKED_ACTION_WORDS),
                "attempted": attempted,
            },
        )
        if not action:
            break
        action = str(action)
        attempted.append(action)
        clicked.append(action)
        page.wait_for_timeout(600)
    return clicked
