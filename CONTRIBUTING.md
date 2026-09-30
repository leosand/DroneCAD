# Contributing to DroneCAD

Thanks for your interest! Contributions of all sizes are welcome.

## Ways to contribute

- Report bugs and installation problems (Windows, WSL2, Docker).
- Add or improve MCP tools, URDF/CAD examples, and simulation scenarios.
- Improve documentation and translations.
- Add tests and benchmarks (local models, GPUs).

## Before you start

1. Browse the [open issues](https://github.com/leosand/DroneCAD/issues).
2. For anything larger than a small fix, open an issue first so we can agree on the approach.

## Development setup

```bash
git clone --recurse-submodules https://github.com/<your-fork>/DroneCAD.git
cd DroneCAD
cp .env.example .env   # never commit .env
docker compose up -d --build
```

See [docs/USAGE.md](docs/USAGE.md) for usage and [docs/TESTING.md](docs/TESTING.md) for running the tests.

## Workflow

1. Fork the repository and create a branch: `feat/...`, `fix/...` or `docs/...`.
2. Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat: ...`, `fix: ...`, `docs: ...`).
3. Make sure CI (`.github/workflows/ci.yml`) passes and your change is covered by tests where applicable.
4. Update `CHANGELOG.md` and the relevant documentation.
5. Open a pull request using the provided template.

## Rules

- Never commit secrets, tokens or keys.
- Do not edit `vendor/` directly; propose changes upstream.
- Sign off your commits (`git commit -s`) to certify the [Developer Certificate of Origin](https://developercertificate.org/).
- Follow the [Code of Conduct](CODE_OF_CONDUCT.md).
- Report vulnerabilities privately, see [SECURITY.md](SECURITY.md).

## AI coding agents

Agent-specific instructions live in [AGENTS.md](AGENTS.md). Human review is required for all agent-generated changes.
