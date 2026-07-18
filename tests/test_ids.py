from cryptofactors.ids import canonical_json_bytes, fingerprint


def test_canonical_json_is_order_independent() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == canonical_json_bytes({"a": 1, "b": 2})


def test_fingerprint_changes_with_input() -> None:
    assert fingerprint("ds", {"a": 1}) != fingerprint("ds", {"a": 2})
