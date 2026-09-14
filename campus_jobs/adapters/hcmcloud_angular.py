from __future__ import annotations

import json

from .hcmcloud import HCMCloudAdapter as _HCMCloudAdapter


class HCMCloudAdapter(_HCMCloudAdapter):
    """HCMCloud adapter with an AngularJS-aware pager driver.

    Older HCMCloud portals expose paging through ``hc-paging``. Its public
    ``refreshPage(target)`` method is the stable path: it updates the pager's
    internal page state and calls ``onPagingChange()``, which in turn asks the
    job-list controller to fetch that page. We only accept the transition after
    both the visible page number and the first rendered ``hcm-key`` change.
    """

    def __init__(self) -> None:
        self._last_pager_debug: dict[str, object] = {}

    @staticmethod
    def _pager_page(page) -> int | None:
        try:
            value = page.evaluate(
                r"""
                () => {
                  const input = document.querySelector(
                    '.hc-paging input[ng-model="paging.current_page"]'
                  );
                  if (!input) return null;
                  const value = Number(input.value);
                  return Number.isFinite(value) ? value : null;
                }
                """
            )
            return int(value) if value is not None else None
        except Exception:
            return None

    @staticmethod
    def _first_row_key(page) -> str:
        try:
            return str(
                page.evaluate(
                    r"""() => {
                      const row = document.querySelector('.table-row[hcm-key]');
                      return row ? (row.getAttribute('hcm-key') || '') : '';
                    }"""
                )
                or ""
            )
        except Exception:
            return ""

    @classmethod
    def _wait_for_transition(
        cls,
        page,
        target_page: int,
        previous_key: str,
        *,
        timeout: int = 14000,
    ) -> bool:
        try:
            page.wait_for_function(
                r"""
                ([target, previous]) => {
                  const input = document.querySelector(
                    '.hc-paging input[ng-model="paging.current_page"]'
                  );
                  const row = document.querySelector('.table-row[hcm-key]');
                  return input
                    && Number(input.value) === target
                    && row
                    && row.getAttribute('hcm-key')
                    && row.getAttribute('hcm-key') !== previous;
                }
                """,
                [target_page, previous_key],
                timeout=timeout,
            )
            return True
        except Exception:
            return False

    @staticmethod
    def _refresh_page(page, target_page: int) -> dict[str, object]:
        """Invoke HCMCloud's native pager transition for an explicit page."""
        try:
            result = page.evaluate(
                r"""
                (target) => {
                  const debug = {target, angularFound: !!window.angular, method: ''};
                  const ng = window.angular;
                  if (!ng) return debug;

                  const button = document.querySelector(
                    `.hc-paging [ng-click*="onPagingClick('next')"]`
                  );
                  debug.pagerFound = !!button;
                  if (!button) return debug;

                  try {
                    const scope = ng.element(button).scope();
                    debug.scopeFound = !!scope;
                    debug.hasPaging = !!scope && !!scope.paging;
                    if (!scope || !scope.paging) return debug;

                    const paging = scope.paging;
                    debug.currentBefore = paging.current_page;
                    debug.internalBefore = paging._current_page;
                    debug.pageCount = paging.page_count;
                    debug.pageSize = paging.page_size;
                    debug.outsideCanRefresh = paging.outsideCanRefresh;
                    debug.hasRefreshPage = typeof paging.refreshPage === 'function';
                    debug.hasOnPagingChange = typeof paging.onPagingChange === 'function';
                    if (typeof paging.refreshPage !== 'function') return debug;
                    if (target < 1 || target > Number(paging.page_count || 0)) {
                      debug.method = 'invalid-target';
                      return debug;
                    }

                    const run = () => paging.refreshPage(target);
                    if (scope.$$phase) run();
                    else scope.$apply(run);

                    debug.method = 'paging.refreshPage(target)';
                    debug.currentAfter = paging.current_page;
                    debug.internalAfter = paging._current_page;
                    return debug;
                  } catch (error) {
                    debug.error = String(error && error.message || error);
                    return debug;
                  }
                }
                """,
                target_page,
            )
            return result if isinstance(result, dict) else {"method": str(result or "")}
        except Exception as exc:
            return {
                "method": "refresh-evaluate-error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    def _advance_page(self, page, target_page: int, previous_key: str) -> str:
        self._last_pager_debug = {
            "target": target_page,
            "currentBefore": self._pager_page(page),
            "previousKey": previous_key,
        }

        for attempt in range(2):
            refresh = self._refresh_page(page, target_page)
            self._last_pager_debug[f"attempt{attempt + 1}"] = refresh
            method = str(refresh.get("method") or "")
            if method == "invalid-target":
                return ""
            if method and self._wait_for_transition(
                page,
                target_page,
                previous_key,
                timeout=14000,
            ):
                self._last_pager_debug["currentAfter"] = self._pager_page(page)
                self._last_pager_debug["firstKeyAfter"] = self._first_row_key(page)
                return f"hc-paging-refresh:{target_page}"

            # If the portal is still completing the first request, do not issue a
            # rapid duplicate transition. One bounded settle window keeps paging
            # deterministic while still allowing a single retry for transient UI
            # failures.
            page.wait_for_timeout(1200)
            if self._pager_page(page) == target_page and self._first_row_key(page) != previous_key:
                return f"hc-paging-delayed:{target_page}"

        self._last_pager_debug["currentFinal"] = self._pager_page(page)
        self._last_pager_debug["firstKeyFinal"] = self._first_row_key(page)
        return ""

    def crawl(self, url, options):
        result = super().crawl(url, options)
        if any(w.startswith("QUALITY_FAIL pagination") for w in result.warnings):
            result.warnings.append(
                "HCMCloud pager debug: "
                + json.dumps(self._last_pager_debug, ensure_ascii=False, default=str)
            )
        return result
