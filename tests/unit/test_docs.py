"""Documentation drift gate.

The docs state facts that the tooling also defines: test counts, quality-gate
commands, size caps, the coverage floor, the Python version. Each fact has a
machine-readable source of truth; this gate fails when a doc claim and its
source disagree, naming the file and both values. Only anchored patterns are
checked, never prose wording, so rephrasing stays free while numbers cannot
silently rot.
"""

import re
import tomllib

import test_standards

REPO = test_standards.REPO
DOCS = ("README.md", "CONTRIBUTING.md", "AGENTS.md")


def _text(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def _flat(rel: str) -> str:
    """Whitespace-collapsed text, so wrapped lines still match one pattern."""
    return " ".join(_text(rel).split())


def _count_tests(tier: str) -> int:
    files = sorted((REPO / "tests" / tier).rglob("*.py"))
    pattern = re.compile(r"^def test_", re.MULTILINE)
    return sum(len(pattern.findall(p.read_text(encoding="utf-8"))) for p in files)


def test_northstar_test_counts() -> None:
    unit, integration, e2e = (_count_tests(t) for t in ("unit", "integration", "e2e"))
    total = unit + integration + e2e
    text = _flat("NORTHSTAR.md")
    row = re.search(r"(\d+) \((\d+) unit / (\d+) integration / (\d+) e2e\)", text)
    assert row, "NORTHSTAR.md: green-tests row 'N (U unit / I integration / E e2e)' not found"
    found = tuple(int(g) for g in row.groups())
    assert found == (total, unit, integration, e2e), (
        f"NORTHSTAR.md green-tests row says {found}, "
        f"actual is ({total}, {unit}, {integration}, {e2e})"
    )
    duration = re.search(r"\((\d+) tests\)", text)
    assert duration, "NORTHSTAR.md: suite-duration row '(N tests)' not found"
    assert int(duration.group(1)) == total, (
        f"NORTHSTAR.md suite-duration row says {duration.group(1)} tests, actual is {total}"
    )


def _gate_commands() -> list[str]:
    """The quality commands of the justfile `check` recipe (source of truth)."""
    lines = _text("justfile").splitlines()
    start = lines.index("check:") + 1
    block = []
    for line in lines[start:]:
        if not line.startswith(" "):
            break
        block.append(line.strip())
    return [cmd for cmd in block if cmd.startswith("uv run ")]


def test_gate_commands_documented() -> None:
    commands = _gate_commands()
    assert commands, "justfile check recipe: no 'uv run ...' command found"
    for doc in DOCS:
        text = _text(doc)
        missing = [cmd for cmd in commands if cmd not in text]
        assert not missing, f"{doc}: hook commands not quoted verbatim: {missing}"
    ci = _text(".github/workflows/ci.yml")
    missing = [cmd for cmd in commands if f"- run: {cmd}" not in ci]
    assert not missing, f"ci.yml quality job: hook commands missing: {missing}"


def test_gate_commands_in_precommit_hooks() -> None:
    """Ruff runs through its pinned mirror hooks; the venv-bound gate
    commands must stay wired as local-hook entries, or a deleted hook
    would silently drop a local gate."""
    commands = [cmd for cmd in _gate_commands() if not cmd.startswith("uv run ruff")]
    assert commands, "justfile check recipe: no venv-bound 'uv run ...' command found"
    config = _text(".pre-commit-config.yaml")
    missing = [cmd for cmd in commands if f"entry: {cmd}" not in config]
    assert not missing, f".pre-commit-config.yaml: local-hook entries missing: {missing}"


def test_size_caps_documented() -> None:
    module_cap = test_standards.MAX_MODULE_LINES
    script_cap = test_standards.MAX_SCRIPT_LINES
    claims = {
        "CONTRIBUTING.md": r"<= (\d+) lines per module, <= (\d+) per script",
        "AGENTS.md": r"modules <= (\d+) lines, scripts <= (\d+) lines",
    }
    for doc, pattern in claims.items():
        match = re.search(pattern, _flat(doc))
        assert match, f"{doc}: size-cap claim matching {pattern!r} not found"
        found = (int(match.group(1)), int(match.group(2)))
        assert found == (module_cap, script_cap), (
            f"{doc} says caps {found}, test_standards enforces ({module_cap}, {script_cap})"
        )


def _coverage_floor() -> int:
    with (REPO / "pyproject.toml").open("rb") as fh:
        addopts = tomllib.load(fh)["tool"]["pytest"]["ini_options"]["addopts"]
    match = re.search(r"--cov-fail-under=(\d+)", addopts)
    assert match, "pyproject.toml: --cov-fail-under not found in pytest addopts"
    return int(match.group(1))


def test_coverage_floor_documented() -> None:
    floor = _coverage_floor()
    for doc in DOCS:
        claims = re.findall(r"(\d+)% (?:branch-)?coverage floor", _flat(doc))
        assert claims, f"{doc}: no coverage-floor claim found"
        wrong = [c for c in claims if int(c) != floor]
        assert not wrong, f"{doc} claims floor(s) {wrong}%, pyproject enforces {floor}%"
    northstar = re.search(r">= (\d+)% \(enforced floor\)", _flat("NORTHSTAR.md"))
    assert northstar, "NORTHSTAR.md: '>= N% (enforced floor)' row not found"
    assert int(northstar.group(1)) == floor, (
        f"NORTHSTAR.md floor row says {northstar.group(1)}%, pyproject enforces {floor}%"
    )


def test_agents_skills_snapshot_status_documented() -> None:
    """The fresh-machine promise about ~/.agents/skills must match the repo.

    config/agents-skills only exists when the live folder held files at sync
    time (git never versions empty folders), and restore skips sections
    absent from the snapshot. The README must state the snapshot's current
    status, so the restore promise cannot silently diverge from what a
    fresh machine actually gets back.
    """
    snapshot = REPO / "config" / "agents-skills"
    captured = snapshot.is_dir() and any(p.is_file() for p in snapshot.rglob("*"))
    claim = re.search(
        r"`config/agents-skills/` is currently (absent from the repo|captured)",
        _flat("README.md"),
    )
    assert claim, "README.md: agents-skills snapshot status claim not found"
    says_captured = claim.group(1) == "captured"
    assert says_captured == captured, (
        f"README.md says the agents-skills snapshot is "
        f"{'captured' if says_captured else 'absent'}, but config/agents-skills "
        f"{'has files' if captured else 'is absent or empty'}"
    )


def test_release_pr_checks_claim_matches_workflow() -> None:
    """The AGENTS.md release-PR quirk must track the workflow's token logic.

    release-please pushes the release PR with RELEASE_PLEASE_TOKEN when the
    secret exists (PR gets CI like any branch) and falls back to github.token
    otherwise (GitHub anti-recursion: no checks). The doc claim must stay
    conditional as long as the workflow carries that fallback.
    """
    workflow = _text(".github/workflows/release-please.yml")
    assert "secrets.RELEASE_PLEASE_TOKEN || github.token" in workflow, (
        "release-please.yml: token fallback expression is gone; rewrite the "
        "AGENTS.md release-PR checks quirk for the new unconditional behavior"
    )
    claim = re.search(
        r"release-please PRs run CI only when the `RELEASE_PLEASE_TOKEN` secret exists",
        _flat("AGENTS.md"),
    )
    assert claim, "AGENTS.md: conditional release-PR checks claim not found"


def test_config_exclusion_claim_matches_tooling() -> None:
    """AGENTS.md must name the gates that skip config/ and only those.

    config/ is excluded from the style gates (ADR-0003) but gitleaks scans
    its full history and pytest exercises snapshot behavior, so a claim of
    blanket exclusion would be false. Each named style gate must actually
    exclude config/ in its configuration.
    """
    with (REPO / "pyproject.toml").open("rb") as fh:
        tool = tomllib.load(fh)["tool"]
    assert "config" in tool["ruff"]["extend-exclude"], "pyproject: ruff no longer excludes config/"
    assert "config" in tool["deptry"]["extend_exclude"], (
        "pyproject: deptry no longer excludes config/"
    )
    assert "config/ (live-config snapshot)" in _text("tests/unit/test_language.py"), (
        "test_language.py: config/ exclusion note is gone"
    )
    claim = re.search(
        r"excluded from the style gates \(Ruff, deptry, the language scan - ADR-0003\); "
        r"gitleaks and the test suite still cover it",
        _flat("AGENTS.md"),
    )
    assert claim, "AGENTS.md: narrowed config/ style-gate exclusion claim not found"


def _ruff_caps() -> tuple[int, int, int, int]:
    with (REPO / "pyproject.toml").open("rb") as fh:
        ruff = tomllib.load(fh)["tool"]["ruff"]
    return (
        ruff["line-length"],
        ruff["lint"]["mccabe"]["max-complexity"],
        ruff["lint"]["pylint"]["max-statements"],
        ruff["lint"]["pylint"]["max-args"],
    )


def test_ruff_caps_documented() -> None:
    line, complexity, statements, args = _ruff_caps()
    claims = {
        "README.md": (
            r"line length (\d+)\): cyclomatic complexity \*\*max (\d+)\*\*, "
            r"\*\*max (\d+) statements\*\* and \*\*max (\d+) arguments\*\*",
            (line, complexity, statements, args),
        ),
        "AGENTS.md": (
            r"McCabe <= (\d+), <= (\d+) statements and <= (\d+) arguments per function, "
            r"lines <= (\d+)",
            (complexity, statements, args, line),
        ),
        "CONTRIBUTING.md": (
            r"\(McCabe\) <= (\d+) - <= (\d+) statements per function, <= (\d+) arguments - "
            r"Lines <= (\d+) characters",
            (complexity, statements, args, line),
        ),
    }
    for doc, (pattern, expected) in claims.items():
        match = re.search(pattern, _flat(doc))
        assert match, f"{doc}: ruff caps claim matching {pattern!r} not found"
        found = tuple(int(g) for g in match.groups())
        assert found == expected, f"{doc} says ruff caps {found}, pyproject enforces {expected}"


def test_python_version_documented() -> None:
    with (REPO / "pyproject.toml").open("rb") as fh:
        requires = tomllib.load(fh)["project"]["requires-python"]
    version = requires.removeprefix(">=")
    badge = re.search(r"python-(\d+\.\d+)%2B", _text("README.md"))
    assert badge, "README.md: python version badge not found"
    assert badge.group(1) == version, (
        f"README.md badge says {badge.group(1)}+, pyproject requires {requires}"
    )
    agents = re.search(r"Python (\d+\.\d+)\+", _text("AGENTS.md"))
    assert agents, "AGENTS.md: 'Python N.NN+' claim not found"
    assert agents.group(1) == version, (
        f"AGENTS.md says Python {agents.group(1)}+, pyproject requires {requires}"
    )
