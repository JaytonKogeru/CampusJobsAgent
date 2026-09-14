from __future__ import annotations

import json

from .hcmcloud import HCMCloudAdapter as _HCMCloudAdapter


class HCMCloudAdapter(_HCMCloudAdapter):
    """HCMCloud adapter with an AngularJS-aware pager driver."""

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
    def _invoke_angular_next(page) -> dict[str, object]:
        try:
            result = page.evaluate(
                r"""
                () => {
                  const selector = `.hc-paging [ng-click*="onPagingClick('next')"]`;
                  const button = document.querySelector(selector);
                  const input = document.querySelector(
                    '.hc-paging input[ng-model="paging.current_page"]'
                  );
                  const firstRow = document.querySelector('.table-row[hcm-key]');
                  const debug = {
                    selector,
                    buttonFound: !!button,
                    buttonClass: button ? String(button.className || '') : '',
                    angularFound: !!window.angular,
                    inputBefore: input ? input.value : null,
                    firstKeyBefore: firstRow ? firstRow.getAttribute('hcm-key') : null,
                    scopes: [],
                    method: '',
                  };
                  if (!button) {
                    debug.method = 'missing-button';
                    return debug;
                  }
                  if (/(^|\s)disable(\s|$)/.test(button.className || '')) {
                    debug.method = 'disabled';
                    return debug;
                  }

                  const ng = window.angular;
                  if (ng) {
                    const nodes = [
                      ['button', button],
                      ['paging-box', button.closest('.paging-box')],
                      ['hc-paging-div', button.closest('.hc-paging')],
                      ['hc-paging-host', document.querySelector('hc-paging')],
                    ];
                    for (const [label, node] of nodes) {
                      if (!node) continue;
                      try {
                        const wrapped = ng.element(node);
                        const isolate = typeof wrapped.isolateScope === 'function'
                          ? wrapped.isolateScope() : null;
                        const normal = typeof wrapped.scope === 'function'
                          ? wrapped.scope() : null;
                        for (const [kind, scope] of [['isolate', isolate], ['scope', normal]]) {
                          if (!scope) continue;
                          const entry = {
                            label,
                            kind,
                            hasOnPagingClick: typeof scope.onPagingClick === 'function',
                            currentPage: scope.paging ? scope.paging.current_page : null,
                            pageCount: scope.paging ? scope.paging.page_count : null,
                            pageSize: scope.paging ? scope.paging.page_size : null,
                          };
                          debug.scopes.push(entry);
                          if (entry.hasOnPagingClick) {
                            const run = () => scope.onPagingClick('next');
                            if (scope.$$phase) run();
                            else scope.$apply(run);
                            debug.method = `angular:${label}:${kind}`;
                            debug.inputAfter = input ? input.value : null;
                            debug.scopeCurrentAfter = scope.paging
                              ? scope.paging.current_page : null;
                            return debug;
                          }
                        }
                      } catch (error) {
                        debug.scopes.push({
                          label,
                          error: String(error && error.message || error),
                        });
                      }
                    }
                  }

                  button.click();
                  debug.method = 'dom-click';
                  debug.inputAfter = input ? input.value : null;
                  return debug;
                }
                """
            )
            return result if isinstance(result, dict) else {"method": str(result or "")}
        except Exception as exc:
            return {"method": "evaluate-error", "error": f"{type(exc).__name__}: {exc}"}

    @classmethod
    def _wait_for_target_page(
        cls,
        page,
        target_page: int,
        previous_key: str,
        *,
        timeout: int = 9000,
    ) -> bool:
        try:
            page.wait_for_function(
                r"""
                (target) => {
                  const input = document.querySelector(
                    '.hc-paging input[ng-model="paging.current_page"]'
                  );
                  return input && Number(input.value) === target;
                }
                """,
                target_page,
                timeout=min(timeout, 5000),
            )
        except Exception:
            return False

        if cls._wait_for_row_change(page, previous_key, timeout=timeout):
            return True
        page.wait_for_timeout(1500)
        try:
            first_key = page.evaluate(
                r"""() => {
                  const row = document.querySelector('.table-row[hcm-key]');
                  return row ? (row.getAttribute('hcm-key') || '') : '';
                }"""
            )
            return bool(first_key and first_key != previous_key)
        except Exception:
            return False

    def _advance_page(self, page, target_page: int, previous_key: str) -> str:
        current = self._pager_page(page)
        self._last_pager_debug = {
            "target": target_page,
            "currentBefore": current,
            "previousKey": previous_key,
            "attempts": [],
        }
        if current is not None and current >= target_page:
            if self._wait_for_row_change(page, previous_key, timeout=2500):
                return f"hc-paging-already:{current}"

        for attempt in range(2):
            detail = self._invoke_angular_next(page)
            self._last_pager_debug["attempts"].append(detail)
            method = str(detail.get("method") or "")
            if method == "disabled":
                return ""
            if method and self._wait_for_target_page(
                page,
                target_page,
                previous_key,
                timeout=9000,
            ):
                self._last_pager_debug["currentAfter"] = self._pager_page(page)
                return f"hc-paging-{method}:{attempt + 1}"

            observed = self._pager_page(page)
            self._last_pager_debug["observedAfterAttempt"] = observed
            if observed == target_page:
                if self._wait_for_row_change(page, previous_key, timeout=12000):
                    return f"hc-paging-delayed:{target_page}"
                return ""
            page.wait_for_timeout(1000)

        self._last_pager_debug["currentFinal"] = self._pager_page(page)
        return ""

    def crawl(self, url, options):
        result = super().crawl(url, options)
        if any(w.startswith("QUALITY_FAIL pagination") for w in result.warnings):
            result.warnings.append(
                "HCMCloud pager debug: "
                + json.dumps(self._last_pager_debug, ensure_ascii=False, default=str)
            )
        return result
