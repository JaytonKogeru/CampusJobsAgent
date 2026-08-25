from __future__ import annotations

import random
import time
from typing import Any

import httpx

from .utils import assert_public_url, safe_resolve_host

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
)


class PublicClient:
    def __init__(self, timeout: float = 25.0):
        self.timeout = timeout
        self.client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
        )

    def close(self):
        self.client.close()

    def request(self, method: str, url: str, *, retries: int = 2, **kwargs: Any) -> httpx.Response:
        assert_public_url(url)
        safe_resolve_host(url)
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                r = self.client.request(method, url, **kwargs)
                if r.status_code in {429, 500, 502, 503, 504} and attempt < retries:
                    time.sleep((0.8 * (2**attempt)) + random.random() * 0.25)
                    continue
                r.raise_for_status()
                return r
            except (httpx.HTTPError, OSError) as exc:
                last = exc
                if attempt >= retries:
                    raise
                time.sleep((0.8 * (2**attempt)) + random.random() * 0.25)
        assert last is not None
        raise last

    def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
