# Validation record

Validated in the build environment on 24 September 2026.

- `python -m pytest -q`: **20 passed**. Coverage includes five error rules, redaction, authenticated setup and sessions, scrypt password storage, CSRF/origin checks, login throttling, Viewer/Engineer/Admin permissions, account deactivation and session revocation, password rotation, optimistic concurrency, monitor deduplication and recovery, monitor retention, optional AI adapter behavior, v1 database migration, and static/API validation.
- `npm run build`: **passed**, using Vite 6.3.5 and React 19.1.0.
- The compiled frontend is included in `frontend/dist`.
- An end-to-end browser script was prepared for admin setup, team creation, real HTTP fault/recovery, resolution, logout, Viewer permissions, and mobile overflow. It reached browser launch, but Chromium extraction failed in the build container, so no browser result is claimed.
- Windows execution was not run in this Linux build environment. The launcher and VS Code debugger configuration are included.

These are functional checks on synthetic examples, not an accuracy benchmark, penetration test, or production readiness certification. Run the demo on your laptop before publishing claims or recording a video.
