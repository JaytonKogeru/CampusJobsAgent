from __future__ import annotations

import json

from .hcmcloud import HCMCloudAdapter as _HCMCloudAdapter


class HCMCloudAdapter(_HCMCloudAdapter):
    """HCMCloud adapter with an AngularJS-aware pager driver.

    HCMCloud's ``hc-paging`` directive can update its page-number model without
    refreshing the job table. For these older portals we drive the job-list
    controller itself and only accept a transition after the first rendered
    ``hcm-key`` changes.
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
        timeout: int = 12000,
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
    def _controller_fetch(page, target_page: int) -> dict[str, object]:
        """Ask the list controller to fetch one explicit page."""
        try:
            result = page.evaluate(
                r"""
                (target) => {
                  const ng = window.angular;
                  const source = (fn) => typeof fn === 'function'
                    ? String(fn).replace(/\s+/g, ' ').slice(0, 1800)
                    : '';
                  const debug = {
                    target,
                    angularFound: !!ng,
                    method: '',
                  };
                  if (!ng) return debug;

                  const searchButton = document.querySelector(
                    '.job-search-bar [ng-click*="fetchData"]'
                  );
                  debug.searchButtonFound = !!searchButton;
                  if (!searchButton) return debug;

                  try {
                    const wrapped = ng.element(searchButton);
                    const scopes = [];
                    if (typeof wrapped.scope === 'function') scopes.push(wrapped.scope());
                    let parent = scopes[0] && scopes[0].$parent;
                    for (let depth = 0; parent && depth < 5; depth++, parent = parent.$parent) {
                      scopes.push(parent);
                    }

                    for (let index = 0; index < scopes.length; index++) {
                      const scope = scopes[index];
                      if (!scope) continue;
                      const hasPaging = !!scope.paging;
                      const hasFetchData = typeof scope.fetchData === 'function';
                      debug[`scope${index}`] = {
                        hasPaging,
                        hasFetchData,
                        currentPage: hasPaging ? scope.paging.current_page : null,
                        pageCount: hasPaging ? scope.paging.page_count : null,
                        pageSize: hasPaging ? scope.paging.page_size : null,
                        fetchDataSource: source(scope.fetchData),
                        onPagingChangeSource: hasPaging
                          ? source(scope.paging.onPagingChange) : '',
                        refreshPageSource: hasPaging
                          ? source(scope.paging.refreshPage) : '',
                        canRefreshSource: hasPaging
                          ? source(scope.paging._canRefresh) : '',
                      };
                      if (!hasPaging || !hasFetchData) continue;

                      const run = () => {
                        scope.paging.current_page = target;
                        scope.fetchData();
                      };
                      if (scope.$$phase) run();
                      else scope.$apply(run);
                      debug.method = `job-list.fetchData:scope${index}`;
                      debug.currentAfter = scope.paging.current_page;
                      return debug;
                    }
                  } catch (error) {
                    debug.error = String(error && error.message || error);
                  }
                  return debug;
                }
                """,
                target_page,
            )
            return result if isinstance(result, dict) else {"method": str(result or "")}
        except Exception as exc:
            return {
                "method": "controller-evaluate-error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    @staticmethod
    def _pager_refresh(page, target_page: int) -> dict[str, object]:
        """Fallback to the pager object's public refresh method."""
        try:
            result = page.evaluate(
                r"""
                (target) => {
                  const ng = window.angular;
                  const source = (fn) => typeof fn === 'function'
                    ? String(fn).replace(/\s+/g, ' ').slice(0, 1800)
                    : '';
                  const debug = {target, angularFound: !!ng, method: ''};
                  if (!ng) return debug;
                  const button = document.querySelector(
                    `.hc-paging [ng-click*="onPagingClick('next')"]`
                  );
                  if (!button) return debug;
                  try {
                    const scope = ng.element(button).scope();
                    if (!scope || !scope.paging) return debug;
                    debug.currentBefore = scope.paging.current_page;
                    debug.pageSize = scope.paging.page_size;
                    debug.pageCount = scope.paging.page_count;
                    debug.functions = Object.keys(scope.paging).filter(
                      (key) => typeof scope.paging[key] === 'function'
                    );
                    debug.onPagingClickSource = source(scope.onPagingClick);
                    debug.onPagingChangeSource = source(scope.paging.onPagingChange);
                    debug.refreshPageSource = source(scope.paging.refreshPage);
                    if (typeof scope.paging.refreshPage !== 'function') return debug;
                    const run = () => {
                      scope.paging.current_page = target;
                      scope.paging.refreshPage();
                    };
                    if (scope.$$phase) run();
                    else scope.$apply(run);
                    debug.method = 'paging.refreshPage';
                    debug.currentAfter = scope.paging.current_page;
                  } catch (error) {
                    debug.error = String(error && error.message || error);
                  }
                  return debug;
                }
                """,
                target_page,
            )
            return result if isinstance(result, dict) else {"method": str(result or "")}
        except Exception as exc:
            return {
                "method": "pager-evaluate-error",
                "error": f"{type(exc).__name__}: {exc}",
            }

    def _advance_page(self, page, target_page: int, previous_key: str) -> str:
        self._last_pager_debug = {
            "target": target_page,
            "currentBefore": self._pager_page(page),
            "previousKey": previous_key,
        }

        controller = self._controller_fetch(page, target_page)
        self._last_pager_debug["controller"] = controller
        if controller.get("method") and self._wait_for_transition(
            page,
            target_page,
            previous_key,
            timeout=12000,
        ):
            self._last_pager_debug["currentAfter"] = self._pager_page(page)
            self._last_pager_debug["firstKeyAfter"] = self._first_row_key(page)
            return str(controller["method"])

        refresh = self._pager_refresh(page, target_page)
        self._last_pager_debug["pagerRefresh"] = refresh
        if refresh.get("method") and self._wait_for_transition(
            page,
            target_page,
            previous_key,
            timeout=12000,
        ):
            self._last_pager_debug["currentAfter"] = self._pager_page(page)
            self._last_pager_debug["firstKeyAfter"] = self._first_row_key(page)
            return str(refresh["method"])

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
