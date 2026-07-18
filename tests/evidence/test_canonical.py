from cryptofactors.evidence.canonical import canonical_json_bytes, content_sha256


def test_canonical_json_is_order_independent() -> None:
    left = {"b": 2, "a": [3, 1]}
    right = {"a": [3, 1], "b": 2}
    assert canonical_json_bytes(left) == canonical_json_bytes(right)
    assert content_sha256(left) == content_sha256(right)
