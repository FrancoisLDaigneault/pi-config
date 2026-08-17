"""Property-based tests for the secrets redaction engine (Hypothesis).

Every property drives the real public entry point ``redact`` from
``pi_config_tools.secrets`` over generated JSON documents; nothing here
reimplements the redaction logic. The module's own ``SECRET_KEYS`` and
``SECRET_VALUE_RE`` are used only as generation constraints: clean documents
are provably secret-free and planted secrets are provably detectable, so the
assertions stay honest.

The backtick character is banned from the clean-document alphabet and embedded
in every planted secret value, so "this exact secret survived" checks cannot
collide with generated text by accident.
"""

import copy
import json
from collections.abc import Callable

from hypothesis import given
from hypothesis import strategies as st

from pi_config_tools.secrets import SECRET_KEYS, SECRET_VALUE_RE, redact

_MARKER = "`"
_CHARS = st.characters(exclude_characters=_MARKER)
_PATTERN_PREFIXES = ("sk-", "ghp_", "gho_", "github_pat_", "xoxb-", "Bearer ")
_KEY_CASES: tuple[Callable[[str], str], ...] = (str.lower, str.upper, str.title)
_SORTED_SECRET_KEYS = tuple(sorted(SECRET_KEYS))

_SPECS = st.lists(
    st.tuples(
        st.booleans(),
        st.integers(0, 10**6),
        st.integers(0, 10**6),
        st.integers(0, 10**6),
        st.integers(0, 10**6),
    ),
    min_size=1,
    max_size=5,
)


def _clean_text() -> st.SearchStrategy[str]:
    return st.text(alphabet=_CHARS, max_size=30).filter(lambda s: not SECRET_VALUE_RE.match(s))


def _clean_keys() -> st.SearchStrategy[str]:
    return st.text(alphabet=_CHARS, max_size=15).filter(lambda s: s.lower() not in SECRET_KEYS)


def _scalars() -> st.SearchStrategy[object]:
    return (
        st.none()
        | st.booleans()
        | st.integers(min_value=-(10**9), max_value=10**9)
        | st.floats(allow_nan=False, allow_infinity=False)
        | _clean_text()
    )


def _clean_docs() -> st.SearchStrategy[dict[str, object]]:
    nested = st.recursive(
        _scalars(),
        lambda children: (
            st.lists(children, max_size=4) | st.dictionaries(_clean_keys(), children, max_size=4)
        ),
        max_leaves=12,
    )
    return st.dictionaries(_clean_keys(), nested, max_size=5)


def _walk(node: object, dicts: list[dict[str, object]], seqs: list[list[object]]) -> None:
    if isinstance(node, dict):
        dicts.append(node)
        for value in node.values():
            _walk(value, dicts, seqs)
    elif isinstance(node, list):
        seqs.append(node)
        for value in node:
            _walk(value, dicts, seqs)


def _inject_one(
    spec: tuple[bool, int, int, int, int],
    tag: int,
    dicts: list[dict[str, object]],
    seqs: list[list[object]],
) -> str:
    """Plant one secret; returns the value that must not survive redaction."""
    key_based, site, case_idx, prefix_idx, pos = spec
    if key_based:
        target = dicts[site % len(dicts)]
        case = _KEY_CASES[case_idx % len(_KEY_CASES)]
        key = case(_SORTED_SECRET_KEYS[site % len(_SORTED_SECRET_KEYS)])
        value = f"{_MARKER}hunter2-{tag}"  # no pattern prefix: the key alone must trigger
        target[key] = value
        return value
    value = _PATTERN_PREFIXES[prefix_idx % len(_PATTERN_PREFIXES)] + f"{_MARKER}inj-{tag}"
    containers: list[dict[str, object] | list[object]] = [*dicts, *seqs]
    chosen = containers[site % len(containers)]
    if isinstance(chosen, dict):
        chosen[f"inj{_MARKER}{tag}"] = value
    else:
        chosen.insert(pos % (len(chosen) + 1), value)
    return value


@st.composite
def _docs_with_secrets(draw: st.DrawFn) -> tuple[dict[str, object], list[str]]:
    doc = draw(_clean_docs())
    dicts: list[dict[str, object]] = []
    seqs: list[list[object]] = []
    _walk(doc, dicts, seqs)
    specs = draw(_SPECS)
    planted = [_inject_one(spec, tag, dicts, seqs) for tag, spec in enumerate(specs)]
    return doc, planted


def _assert_same_shape(before: object, after: object) -> None:
    assert type(before) is type(after)
    if isinstance(before, dict):
        assert isinstance(after, dict)
        assert before.keys() == after.keys()
        for key in before:
            _assert_same_shape(before[key], after[key])
    elif isinstance(before, list):
        assert isinstance(after, list)
        assert len(before) == len(after)
        for pair in zip(before, after, strict=True):
            _assert_same_shape(pair[0], pair[1])
    elif before != after:
        assert isinstance(before, str), "only string leaves may ever change"
        assert after == "<REDACTED>", f"leaf changed to {after!r}, not '<REDACTED>'"


@given(doc=_clean_docs())
def test_clean_documents_pass_through_untouched(doc: dict[str, object]) -> None:
    before = json.dumps(doc)
    assert redact(doc) == []
    assert json.dumps(doc) == before


@given(payload=_docs_with_secrets())
def test_no_planted_secret_survives(payload: tuple[dict[str, object], list[str]]) -> None:
    doc, planted = payload
    found = redact(doc)
    dumped = json.dumps(doc)
    assert found, "at least one planted secret must be reported"
    for value in planted:
        assert value not in dumped, f"planted secret {value!r} survived redaction"


@given(payload=_docs_with_secrets())
def test_structure_and_clean_values_preserved(
    payload: tuple[dict[str, object], list[str]],
) -> None:
    doc, _ = payload
    snapshot = copy.deepcopy(doc)
    redact(doc)
    _assert_same_shape(snapshot, doc)


@given(payload=_docs_with_secrets())
def test_redaction_is_idempotent_on_documents(
    payload: tuple[dict[str, object], list[str]],
) -> None:
    doc, _ = payload
    redact(doc)
    after_first = json.dumps(doc)
    redact(doc)
    assert json.dumps(doc) == after_first


def _wild_json() -> st.SearchStrategy[object]:
    scalars = st.none() | st.booleans() | st.integers() | st.floats() | st.text(max_size=200)
    return st.recursive(
        scalars,
        lambda children: (
            st.lists(children, max_size=6)
            | st.dictionaries(st.text(max_size=20), children, max_size=6)
        ),
        max_leaves=25,
    )


@given(doc=_wild_json())
def test_redact_is_total_on_any_json_document(doc: object) -> None:
    redact(doc)  # must never raise, whatever the shape
    json.dumps(doc)  # and must leave the document JSON-serializable


@given(prefix=st.sampled_from(_PATTERN_PREFIXES), suffix=st.text(max_size=20))
def test_top_level_secret_string_is_reported(prefix: str, suffix: str) -> None:
    """A bare secret string at the document root is reported (gap fixed)."""
    assert redact(prefix + suffix), "top-level secret string was not reported"
