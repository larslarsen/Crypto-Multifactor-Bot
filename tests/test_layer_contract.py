from cryptofactors.layer_contract import Layer, NETWORK_ALLOWED, import_is_allowed


def test_research_cannot_import_ingest_or_execution() -> None:
    assert not import_is_allowed(Layer.FACTORS, Layer.INGEST)
    assert not import_is_allowed(Layer.EXPERIMENTS, Layer.EXECUTION)


def test_execution_can_use_serving_but_not_experiments() -> None:
    assert import_is_allowed(Layer.EXECUTION, Layer.SERVING)
    assert not import_is_allowed(Layer.EXECUTION, Layer.EXPERIMENTS)


def test_only_ingest_and_execution_have_network_permission() -> None:
    assert NETWORK_ALLOWED == {Layer.INGEST, Layer.EXECUTION}
