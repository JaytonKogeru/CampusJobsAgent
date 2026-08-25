from __future__ import annotations

import base64
import json
import re
from urllib.parse import urlparse

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from campus_jobs.http import PublicClient
from campus_jobs.models import CrawlOptions, CrawlResult, Job
from campus_jobs.utils import clean_text, unique_keep_order
from .base import BaseAdapter


class MokaAdapter(BaseAdapter):
    name = "moka"
    priority = 100
    MAX_PAGE_SIZE = 50

    @classmethod
    def can_handle(cls, url: str) -> bool:
        return (urlparse(url).hostname or "").lower() == "app.mokahr.com"

    @staticmethod
    def _parse_portal(url: str) -> tuple[str, str, int]:
        # /campus-recruitment/aftershokzhr/36940 or /recommendation-apply/ti/143987
        parts = [x for x in urlparse(url).path.split("/") if x]
        if len(parts) < 3:
            raise ValueError("Unsupported Moka portal URL")
        kind, org, site_raw = parts[0], parts[1], parts[2]
        if not re.fullmatch(r"\d+", site_raw):
            raise ValueError("Moka siteId not found in URL")
        return kind, org, int(site_raw)

    @staticmethod
    def _init_data(html: str) -> dict:
        m = re.search(r'<input[^>]+id=["\']init-data["\'][^>]+value=["\']([^"\']+)["\']', html, re.I)
        if not m:
            return {}
        import html as html_mod
        return json.loads(html_mod.unescape(m.group(1)))

    @staticmethod
    def _decrypt(envelope: dict, aes_iv: str) -> dict:
        data = envelope.get("data")
        key = envelope.get("necromancer")
        if not data or not key or not aes_iv:
            return {}
        decryptor = Cipher(algorithms.AES(str(key).encode()), modes.CBC(aes_iv.encode())).decryptor()
        padded = decryptor.update(base64.b64decode(data)) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        raw = unpadder.update(padded) + unpadder.finalize()
        return json.loads(raw.decode("utf-8"))

    def crawl(self, url: str, options: CrawlOptions) -> CrawlResult:
        kind, org, site_id = self._parse_portal(url)
        portal_url = url.split("#", 1)[0]
        jobs: list[Job] = []
        warnings: list[str] = []
        seen: set[str] = set()
        with PublicClient(options.timeout) as client:
            first = client.get(portal_url)
            init = self._init_data(first.text)
            aes_iv = str(init.get("aesIv") or "")
            if not aes_iv:
                raise RuntimeError("Moka init-data/aesIv not found")
            page_size = min(max(options.page_size, 1), self.MAX_PAGE_SIZE)
            for page in range(options.max_pages):
                body = {
                    "orgId": org,
                    "siteId": str(site_id),
                    "limit": page_size,
                    "offset": page * page_size,
                    "needStat": True,
                    "locale": "zh-CN",
                }
                if options.keyword:
                    body["keyword"] = options.keyword
                endpoint = f"https://app.mokahr.com/api/outer/ats-apply/website/jobs/v2?orgId={org}"
                r = client.post(endpoint, json=body, headers={"Referer": portal_url, "Origin": "https://app.mokahr.com", "Accept": "application/json"})
                payload = self._decrypt(r.json(), aes_iv)
                decoded_data = payload.get("data") or {}
                rows = decoded_data.get("jobs") or []
                if not rows:
                    break
                for item in rows:
                    jid = str(item.get("id") or "")
                    if not jid or jid in seen:
                        continue
                    seen.add(jid)
                    locations = []
                    for loc in item.get("locations") or []:
                        if isinstance(loc, dict):
                            locations.append(loc.get("cityName") or loc.get("address") or loc.get("country") or "")
                    job = Job(
                        id=jid,
                        title=clean_text(item.get("title")),
                        url=f"{portal_url}#/job/{jid}",
                        location=" / ".join(unique_keep_order(locations)),
                        department=clean_text((item.get("department") or {}).get("name")),
                        function=clean_text((item.get("zhineng") or {}).get("name")),
                        recruit_type=clean_text(item.get("commitment")),
                        description=clean_text(item.get("jobDescription")),
                        source="app.mokahr.com",
                        extra={**item, "moka_kind": kind, "site_id": site_id, "org": org},
                    )
                    jobs.append(job)
                    if len(jobs) >= options.max_jobs:
                        break
                if len(jobs) >= options.max_jobs or len(rows) < page_size:
                    break

            if options.include_details:
                for job in jobs:
                    try:
                        dr = client.post(
                            "https://app.mokahr.com/api/outer/ats-apply/website/job",
                            json={"orgId": org, "siteId": str(site_id), "jobId": job.id, "locale": "zh-CN"},
                            headers={"Referer": portal_url, "Origin": "https://app.mokahr.com", "Accept": "application/json"},
                        )
                        detail_payload = self._decrypt(dr.json(), aes_iv)
                        decoded_data = detail_payload.get("data") or {}
                        detail = decoded_data.get("job") or decoded_data
                        if isinstance(detail, dict):
                            job.description = clean_text(detail.get("jobDescription")) or job.description
                            job.department = clean_text((detail.get("department") or {}).get("name")) or job.department
                            job.extra.update(detail)
                    except Exception as exc:  # noqa: BLE001
                        warnings.append(f"detail {job.id}: {exc}")
        return CrawlResult(self.name, url, jobs, warnings)
