# Technology baselines

Recommend a baseline; never impose it. The user may accept, replace, or skip
any item without explanation.

## License

Recommend MIT for a simple permissive default, but require the user to choose
explicitly between `MIT` and `UNLICENSED`. MIT requires the approved copyright
holder and year. `UNLICENSED` grants no permission to use, copy, modify, or
distribute the project. Stop if the user needs another license; never
substitute legal terms silently.

## Python

Use for AI/ML, research, data processing, automation, and Python-first APIs.

- Python 3.12+
- `uv` for environments, dependencies, locking, and commands
- Ruff for formatting and linting
- mypy strict mode
- pytest
- GitHub Actions

Setup and verify:

```text
uv lock
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest -q
```

## Rust

Use for performance-sensitive, safety-critical, concurrent, systems, and
resource-constrained software.

- Rust 1.97.1 toolchain with rustfmt, Clippy, and llvm-tools-preview
- cargo-llvm-cov for line and region coverage
- cargo-deny for advisory, license, ban, and source policies
- cargo-shear for unused dependency detection
- Committed Cargo.lock
- GitHub Actions

Setup and verify:

```text
cargo install --locked --version 0.8.7 cargo-llvm-cov
cargo install --locked --version 0.20.2 cargo-deny
cargo install --locked --version 1.13.3 cargo-shear
cargo fmt --all --check
cargo clippy --workspace --all-targets --all-features --locked -- -D warnings
cargo shear --deny-warnings
cargo test --workspace --all-targets --all-features --locked
cargo test --workspace --doc --all-features --locked
cargo doc --workspace --all-features --no-deps --locked
cargo llvm-cov --workspace --all-features --all-targets --locked --fail-under-lines 95 --fail-under-regions 95 --show-missing-lines
cargo deny --locked check
```

## TypeScript

Use for Node.js services, libraries, CLIs, and web-oriented applications.

- Node.js 24.18.x (>=24.18.0 <25)
- pnpm 11.20.0
- TypeScript 7 strict mode with all approved strictness flags
- Biome for formatting, linting, and complexity enforcement
- Vitest with V8 provider for coverage
- Knip for dead code and dependency detection
- Committed pnpm-lock.yaml
- GitHub Actions

Setup and verify:

```text
pnpm install --frozen-lockfile
pnpm exec biome ci . --error-on-warnings
pnpm exec tsc -p tsconfig.json
pnpm exec knip
pnpm exec vitest run --coverage
pnpm dedupe --check
pnpm audit
pnpm audit signatures
```

## Composed projects

Compose the smallest relevant profiles only after the user selects multiple
real components. Keep each component independently buildable. Add one boundary
contract test only when an actual cross-language or network boundary exists.

Do not create a generic full-stack or hybrid template before those components
are selected.
