from __future__ import annotations

import html
import ipaddress
import json
import re
import socket
from collections.abc import Iterable
from urllib.parse import parse_qs, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

TRACKING_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "spm", "source", "from",
    "recommendcode", "track_id", "timestamp", "random", "ts",
}


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text("\n")
    text = html.unescape(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t\u00a0]+", " ", x).strip() for x in text.split("\n")]
    return "\n".join(x for x in lines if x).strip()


def unique_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        value = clean_text(value)
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def canonical_url(raw: str, base: str = "") -> str:
    if not raw:
        return ""
    url = urljoin(base, raw)
    p = urlparse(url)
    if p.scheme not in {"http", "https"} or not p.hostname:
        return ""
    query = parse_qs(p.query, keep_blank_values=True)
    kept: list[str] = []
    for key, vals in query.items():
        if key.lower() in TRACKING_KEYS or key.lower().startswith("utm_"):
            continue
        for val in vals:
            from urllib.parse import quote_plus
            kept.append(f"{quote_plus(key)}={quote_plus(val)}")
    return urlunparse((p.scheme, p.netloc, p.path, p.params, "&".join(kept), p.fragment))


def assert_public_url(url: str) -> str:
    p = urlparse(url)
    if p.scheme not in {"http", "https"} or not p.hostname:
        raise ValueError(f"Only public http/https URLs are supported: {url}")
    host = p.hostname.strip("[]").lower()
    if host == "localhost" or host.endswith(".localhost"):
        raise ValueError("localhost/private hosts are blocked")
    try:
        ip = ipaddress.ip_address(host)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("private/reserved IPs are blocked")
    except ValueError as exc:
        if "blocked" in str(exc):
            raise
    return url


def safe_resolve_host(url: str) -> None:
    """Best-effort DNS SSRF guard. DNS failures are left to the HTTP client."""
    host = urlparse(url).hostname
    if not host:
        return
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return
    for info in infos:
        raw = info[4][0]
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError(f"resolved address is private/reserved: {raw}")


def find_first(obj: object, keys: list[str]) -> object | None:
    if not isinstance(obj, dict):
        return None
    for key in keys:
        if obj.get(key) not in (None, "", []):
            return obj[key]
    return None


def walk_dicts(obj: object):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk_dicts(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk_dicts(value)


def json_loads_loose(text: str) -> object:
    text = text.strip()
    if not text:
        return None
    return json.loads(text)
