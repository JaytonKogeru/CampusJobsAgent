# AGENTS.md — Chat-driven operating protocol

This repository exists so a chat agent can inspect live public careers sites without asking the user to open DevTools.

## Default behavior when the user sends a careers URL

1. Treat the official careers site as the source of truth for what is currently open.
2. If the site is fully readable with the agent's normal web tooling, use it directly.
3. If the site is dynamic, paginated, incomplete, or the current list cannot be verified, use this repository's crawl control plane.
4. Create a GitHub issue titled `[crawl] <company/task>` with a YAML body containing at least `url`, and normally `scope: campus`, `max_jobs`, and `details: true`.
5. Wait for the `Crawl from issue` workflow to finish, then read `runs/issue-<N>/jobs.json` from the default branch.
6. Check `adapter`, `count`, and `warnings` before trusting the output.
7. Rank/filter the returned jobs against the user's supplied resume/profile in the conversation. Do not store the user's resume or personal contact details in this repository unless the user explicitly asks.
8. Cite/identify which roles came from the official crawl when presenting recommendations.

## Failure policy

- Never represent an old search-engine result as a current official opening.
- If an adapter fails, inspect the persisted warning and try the next automatic path (native API -> browser-context API -> generic browser -> web research).
- Fix reusable adapter bugs in this repository when practical instead of asking the user to manually copy XHR responses.
- Do not attempt to bypass login, CAPTCHA, anti-bot challenges, or private systems.
- Some sites may block GitHub-hosted cloud egress. `CAMPUS_JOBS_PROXY` is supported as an optional repository secret, but the user should not be asked to configure it for normal supported sites.

## Issue command schema

```yaml
url: https://company.example/campus
keyword: optional keyword
scope: campus       # campus | intern | social | all
page_size: 50
max_pages: 30
max_jobs: 500
details: true
timeout: 25
```

## Output contract

`runs/issue-<N>/jobs.json` contains:

- `adapter`
- `source_url`
- `count`
- `warnings`
- normalized `jobs[]` with id/title/url/company/location/department/function/recruit_type/description/requirements/source.

## Safety / product boundaries

- Public job discovery and JD reading are allowed.
- Do not submit an application or alter a recruiting account unless the user explicitly requests that action and the relevant tool supports it.
- Do not commit secrets, cookies, sessions, resumes, phone numbers, email addresses, or other personal data to this repository by default.

## Maintenance

- Keep CI green.
- Prefer ATS-family adapters over one-off selectors.
- Preserve bounded pagination and SSRF protections.
- Keep third-party job aggregators out of the default path; official sources are preferred.
- Close E2E test issues after validation so the issue tracker stays clean.
