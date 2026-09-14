from __future__ import annotations

from .hcmcloud import HCMCloudAdapter as _HCMCloudAdapter


class HCMCloudAdapter(_HCMCloudAdapter):
    """HCMCloud adapter with an AngularJS-aware pager driver.

    Older HCMCloud portals expose pagination through the ``hc-paging`` AngularJS
    directive. Native Playwright clicks can be intercepted by the virtual table or
    ignored during a digest. Drive the directive through its own scope first, then
    fall back to the exact DOM handler. Every transition is verified against both
    the visible page-number model and the first rendered ``hcm-key`` row.
    """

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
    def _invoke_angular_next(page) -> str:
        try:
            result = page.evaluate(
                r"""
                () => {
                  const button = document.querySelector(
                    `.hc-paging [ng-click*="onPagingClick('next')"]`
                  );
                  if (!button) return 'missing-button';
                  if (/(^|\s)disable(\s|$)/.test(button.className || '')) {
                    return 'disabled';
                  }

                  const ng = window.angular;
                  if (ng) {
                    const nodes = [
                      button,
                      button.closest('.paging-box'),
                      button.closest('.hc-paging'),
                      document.querySelector('hc-paging'),
                    ].filter(Boolean);
                    for (const node of nodes) {
                      try {
                        const wrapped = ng.element(node);
                        const scope =
                          (typeof wrapped.isolateScope === 'function' && wrapped.isolateScope())
                          || (typeof wrapped.scope === 'function' && wrapped.scope());
                        if (!scope || typeof scope.onPagingClick !== 'function') continue;
                        const run = () => scope.onPagingClick('next');
                        if (scope.$$phase) run();
                        else scope.$apply(run);
                        return 'angular-scope';
                      } catch (_) {
                        // Keep trying parent scopes before using the DOM handler.
                      }
                    }
                  }

                  button.click();
                  return 'dom-click';
                }
                """
            )
            return str(result or "")
        except Exception:
            return ""

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

        # Some builds update the page model before swapping the virtualized rows.
        # Give the table one final bounded settle window, but never accept a page
        # transition solely because the page-number input changed.
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

    @classmethod
    def _advance_page(cls, page, target_page: int, previous_key: str) -> str:
        current = cls._pager_page(page)
        if current is not None and current >= target_page:
            # A prior asynchronous transition completed just before this call.
            if cls._wait_for_row_change(page, previous_key, timeout=2500):
                return f"hc-paging-already:{current}"

        for attempt in range(2):
            method = cls._invoke_angular_next(page)
            if method == "disabled":
                return ""
            if method and cls._wait_for_target_page(
                page,
                target_page,
                previous_key,
                timeout=9000,
            ):
                return f"hc-paging-{method}:{attempt + 1}"

            observed = cls._pager_page(page)
            if observed == target_page:
                # The model advanced but row replacement is still in flight. Do
                # not click again and accidentally skip a page.
                if cls._wait_for_row_change(page, previous_key, timeout=12000):
                    return f"hc-paging-delayed:{target_page}"
                return ""
            page.wait_for_timeout(1000)

        return ""
