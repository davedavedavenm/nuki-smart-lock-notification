# Nuki implementation roadmap

## Status: retired

The directory-restructure plan previously recorded here is obsolete. Its
`phase1/directory-structure` implementation was incomplete, could not run, and
was superseded by the working layout on `main`. The branch was removed on
2026-07-26; it must not be used as an implementation baseline.

The supported source layout is the one documented in `README.md`:

- `scripts/` contains the monitor, configuration tools, and Nuki API package.
- `web/` contains the Flask application and dashboard.
- `security/` contains security monitoring and alerting.
- the root Dockerfiles and `docker-compose.yml` remain the supported container
  layout.
- `tests/` plus the root test modules cover the maintained implementation.

Current deployment and configuration guidance lives in:

- `DOCKER_GUIDE.md`
- `docs/docker-deployment.md`
- `docs/configuration.md`
- `TROUBLESHOOTING.md`

Future work should be represented by a current GitHub issue and implemented on
`main`; do not recreate phase or release branches solely to mirror this retired
plan.
