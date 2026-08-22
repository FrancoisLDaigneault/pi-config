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

import pytest
import test_standards
import yaml

REPO = test_standards.REPO
DOCS = ("README.md", "CONTRIBUTING.md", "AGENTS.md")
GITLEAKS_REPO = "https://github.com/gitleaks/gitleaks"
INSTALL_HOOK_TYPES = ("pre-commit", "pre-merge-commit")

# The hook types declared in a comment instead of in the mapping. A review
# proved the earlier text search accepted this, though it installs nothing.
COMMENTED_INSTALL_TYPES_CONFIG = """
# default_install_hook_types: [pre-commit, pre-merge-commit]
repos: []
"""

# A decoy hook reusing the official id under another repo. A review proved the
# earlier line-matching check accepted it, leaving the real hook unguarded.
DECOY_GITLEAKS_CONFIG = """
repos:
  - repo: local
    hooks:
      - id: gitleaks
        always_run: true
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.3
    hooks:
      - id: gitleaks
"""


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


def _config(raw: str | None = None) -> dict[str, object]:
    """The parsed pre-commit configuration; the shipped file unless overridden.

    Parsing is what makes the assertions below discriminate: text matching
    accepts a claim written in a comment, and an id lookup accepts a same-id
    hook declared under any other repo. `safe_load` accepts neither.
    """
    parsed = yaml.safe_load(_text(".pre-commit-config.yaml") if raw is None else raw)
    assert isinstance(parsed, dict), ".pre-commit-config.yaml: the top level is not a mapping"
    return parsed


def _official_hook(config: dict[str, object], repo_url: str, hook_id: str) -> dict[str, object]:
    """One hook entry, identified by its owning repo and not by its id alone."""
    repos = config.get("repos")
    assert isinstance(repos, list), ".pre-commit-config.yaml: 'repos' is not a list"
    hooks: list[dict[str, object]] = []
    for entry in repos:
        if not isinstance(entry, dict) or entry.get("repo") != repo_url:
            continue
        declared = entry.get("hooks")
        assert isinstance(declared, list), f".pre-commit-config.yaml: {repo_url} has no hook list"
        hooks += [h for h in declared if isinstance(h, dict) and h.get("id") == hook_id]
    assert len(hooks) == 1, (
        f".pre-commit-config.yaml: expected exactly one {hook_id!r} hook under {repo_url}, "
        f"found {len(hooks)}"
    )
    return hooks[0]


def _assert_secrets_gate_always_runs(config: dict[str, object]) -> None:
    """The shared assertion, so the negative test exercises the real check."""
    hook = _official_hook(config, GITLEAKS_REPO, "gitleaks")
    assert hook.get("always_run") is True, (
        ".pre-commit-config.yaml: the gitleaks hook must declare 'always_run: true', "
        "or a commit whose staged files are all excluded skips the secrets gate"
    )


def test_secrets_gate_cannot_be_skipped() -> None:
    """The secrets gate must run on every commit, not only on matching files.

    pre-commit filters the master file list with the top-level `exclude:`
    before any per-hook logic, then skips a hook whose filtered list came out
    empty unless it declares `always_run`. `pass_filenames: false` does not
    exempt it: that flag is read after the skip decision. With `exclude:
    ^config/` set repo-wide, a commit staging only snapshot files would
    otherwise skip gitleaks entirely - precisely where a live-machine secret
    is most likely to enter. AGENTS.md states that gitleaks still covers
    config/; this gate keeps that claim true.
    """
    _assert_secrets_gate_always_runs(_config())


def test_secrets_gate_check_rejects_a_decoy_hook() -> None:
    """A same-id hook under another repo must not satisfy the gate.

    This is the mutation a review used to prove the earlier line-matching
    check was vacuous: it took the first `- id: gitleaks` it found, so a decoy
    carrying `always_run` let the official hook go without it.
    """
    with pytest.raises(AssertionError):
        _assert_secrets_gate_always_runs(_config(DECOY_GITLEAKS_CONFIG))


def _assert_both_hook_types_installed(config: dict[str, object]) -> None:
    """The shared assertion, so the negative test exercises the real check."""
    declared = config.get("default_install_hook_types")
    assert isinstance(declared, list), (
        ".pre-commit-config.yaml: 'default_install_hook_types' must be declared as a "
        "list, or a plain 'pre-commit install' wires the pre-commit type only"
    )
    missing = [hook_type for hook_type in INSTALL_HOOK_TYPES if hook_type not in declared]
    assert not missing, (
        f".pre-commit-config.yaml: 'default_install_hook_types' is missing {missing}, "
        "so git runs no hook on that path"
    )


def test_setup_installs_both_hook_types() -> None:
    """Onboarding must wire pre-merge-commit too, or merges bypass every gate.

    Git does not run the pre-commit hook when a merge commits on its own: it
    runs pre-merge-commit. Installing only the default type leaves that path
    ungated, so a secret arriving through a local merge lands unscanned. The
    types are asserted on the config rather than on an install command, so
    every documented way of installing gets them, not just `just setup`.
    """
    _assert_both_hook_types_installed(_config())


def test_hook_type_check_rejects_a_commented_declaration() -> None:
    """A commented-out declaration must not satisfy the check.

    This is the mutation a review used to prove the earlier text search was
    vacuous: it accepted the install command when it appeared in a comment
    only, which installs nothing at all.
    """
    with pytest.raises(AssertionError):
        _assert_both_hook_types_installed(_config(COMMENTED_INSTALL_TYPES_CONFIG))


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
    agents = _text("AGENTS.md")
    for anchor in ("merge_method=squash", "-f sha=", "verification.verified"):
        assert anchor in agents, (
            f"AGENTS.md: the guarded REST squash runbook for release PRs must "
            f"quote {anchor!r} (required_signatures blocks GraphQL merges of "
            f"unsigned release-please heads)"
        )


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


_NUMBER_WORDS = {4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}


def test_gate_command_count_documented() -> None:
    count = len(_gate_commands())
    assert count in _NUMBER_WORDS, f"justfile check recipe has {count} commands; extend the map"
    word = _NUMBER_WORDS[count]
    claims = {
        "README.md": rf"the {word} full-project gate commands",
        "AGENTS.md": rf"The {word} quality commands",
    }
    for doc, pattern in claims.items():
        assert re.search(pattern, _flat(doc)), (
            f"{doc}: gate-command count claim {pattern!r} not found "
            f"(justfile check recipe has {count} commands)"
        )


def test_ci_schedule_documented() -> None:
    """The documented CI cadence and runner must match ci.yml."""
    ci = _text(".github/workflows/ci.yml")
    cron = re.search(r'cron: "(\d+) (\d+) \* \* (\d+)"', ci)
    assert cron, "ci.yml: weekly cron entry not found"
    minute, hour, dow = (int(g) for g in cron.groups())
    day = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")[dow]
    stamp = rf"{day} (?:at )?{hour:02d}:{minute:02d} UTC"
    for doc in ("README.md", "NORTHSTAR.md"):
        assert re.search(stamp, _flat(doc)), f"{doc}: CI schedule claim {stamp!r} not found"
    runner = re.search(r"\n  quality:\n(?:.+\n)*?    runs-on: (\S+)", ci)
    assert runner, "ci.yml: quality job runs-on not found"
    claim = re.search(r"quality job on `([\w-]+)`", _flat("README.md"))
    assert claim, "README.md: quality-job runner claim not found"
    assert claim.group(1) == runner.group(1), (
        f"README.md says the quality job runs on {claim.group(1)}, ci.yml uses {runner.group(1)}"
    )


def test_security_jobs_documented() -> None:
    """Every non-quality CI job must be named in README.md and SECURITY.md.

    The mapping pins each ci.yml job id to the token the docs use for it;
    adding or removing a job fails here until the docs and the mapping are
    updated together.
    """
    ci = _text(".github/workflows/ci.yml")
    jobs = set(re.findall(r"^  ([a-z][\w-]*):$", ci.split("\njobs:\n", 1)[1], re.MULTILINE))
    tokens = {
        "secrets-scan": "gitleaks",
        "uv-audit": "uv audit --locked",
        "pip-audit": "pip-audit",
        "dependency-review": "Dependency Review",
        "semgrep": "Semgrep",
        "zizmor": "zizmor",
    }
    assert jobs - {"quality"} == set(tokens), (
        f"ci.yml jobs {sorted(jobs - {'quality'})} diverge from the mapping "
        f"{sorted(tokens)}; update README.md, SECURITY.md and this test together"
    )
    for doc in ("README.md", "SECURITY.md"):
        text = _flat(doc)
        missing = [t for t in tokens.values() if t not in text]
        assert not missing, f"{doc}: security scans not mentioned: {missing}"
    severity = re.search(r"fail-on-severity: (\w+)", ci)
    assert severity, "ci.yml: dependency-review fail-on-severity not found"
    claim = re.search(r"(\w+)-or-higher findings blocking", _flat("SECURITY.md"))
    assert claim, "SECURITY.md: dependency-review severity claim not found"
    assert claim.group(1) == severity.group(1), (
        f"SECURITY.md says {claim.group(1)}-or-higher blocks, "
        f"ci.yml sets fail-on-severity {severity.group(1)}"
    )


def test_semgrep_command_documented() -> None:
    quoted = re.search(r"`(uvx semgrep==[^`]+)`", _flat("NORTHSTAR.md"))
    assert quoted, "NORTHSTAR.md: quoted semgrep command not found"
    assert f"- run: {quoted.group(1)}" in _text(".github/workflows/ci.yml"), (
        f"NORTHSTAR.md quotes {quoted.group(1)!r}; ci.yml runs a different semgrep command"
    )


def test_release_assets_documented() -> None:
    """The documented release-asset inventory must match the workflow steps.

    Producer tokens prove each asset is still built; the doc names prove each
    asset is still documented. Removing a workflow step fails here until the
    asset lists in README.md, SECURITY.md and AGENTS.md are updated too.
    """
    workflow = _text(".github/workflows/release-please.yml")
    producers = (
        "uv build",
        "sbom.cdx.json",
        "sbom.spdx.json",
        "SHA256SUMS",
        "attest-build-provenance",
    )
    gone = [p for p in producers if p not in workflow]
    assert not gone, f"release-please.yml: asset-producing steps missing: {gone}"
    names = ("wheel", "sdist", "CycloneDX", "SPDX", "SHA-256", "attestation")
    for doc in ("README.md", "SECURITY.md", "AGENTS.md"):
        text = _flat(doc)
        missing = [n for n in names if n not in text]
        assert not missing, f"{doc}: release assets not mentioned: {missing}"
