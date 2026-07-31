"""DEX-003 — focused pure tests for ADR-0015 §9 v2 foundation.

No network. Covers plan pins, cohort matrix, log identity, splits, receipt+header
authority for coverage, PlanRecord column consistency, O(1) streaming coverage,
and forged/missing-header fail-closed paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from cryptofactors.acquisition.uniswap_v2_pair_events import SWAP_TOPIC, SYNC_TOPIC
from cryptofactors.acquisition.uniswap_v2_pair_events_v2 import (
    ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID,
    CANDIDATE_COHORT_SIZES,
    DEFAULT_INITIAL_COHORT_SIZE,
    ORDERED_EVENT_TOPICS,
    PINNED_FINALITY_CUTOFF_BLOCK,
    CanonicalHeaderReceiptRecord,
    LeafReceiptRecord,
    PairEventV2Error,
    PlanConfig,
    PlanRecord,
    QueryDomain,
    QueryNode,
    RegistryPoolBirth,
    build_acquisition_plan_v2,
    combined_pair_logs_request,
    compute_canonical_header_receipt_id,
    compute_leaf_receipt_id,
    extract_log_identity_v2,
    iter_root_windows,
    log_identity_v2_digest,
    make_leaf_receipt_record,
    normalize_and_index_logs,
    plan_record_from_config,
    prove_full_registry_coverage,
    prove_pool_topic_coverage,
    reconcile_log_sets_v2,
    sort_pool_births,
    split_domain_by_address,
    split_domain_by_block,
    split_node,
    validate_children_partition,
    validate_event_shape,
)

POOL_A = "0x" + "11" * 20
POOL_B = "0x" + "22" * 20
POOL_C = "0x" + "33" * 20
BLOCK = 10_008_355
WORD = "00" * 32


def _addr_topic(byte: int) -> str:
    return "0x" + "00" * 12 + f"{byte:02x}" * 20


def _swap_log(
    *,
    address: str = POOL_A,
    block_number: int = BLOCK,
    block_hash: str | None = None,
    tx_hash: str | None = None,
    tx_index: int = 7,
    log_index: int = 3,
    data: str | None = None,
    removed: bool = False,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "address": address,
        "blockNumber": hex(block_number),
        "blockHash": block_hash or ("0x" + "ab" * 32),
        "transactionHash": tx_hash or ("0x" + "cd" * 32),
        "transactionIndex": hex(tx_index),
        "logIndex": hex(log_index),
        "topics": topics
        if topics is not None
        else [SWAP_TOPIC, _addr_topic(0x22), _addr_topic(0x33)],
        "data": data if data is not None else ("0x" + WORD * 4),
        "removed": removed,
    }


def _sync_log(*, reserve0: int = 1_000, reserve1: int = 2_000) -> dict[str, Any]:
    return {
        "address": POOL_A,
        "blockNumber": hex(BLOCK),
        "blockHash": "0x" + "ef" * 32,
        "transactionHash": "0x" + "12" * 32,
        "transactionIndex": hex(1),
        "logIndex": hex(0),
        "topics": [SYNC_TOPIC],
        "data": "0x" + f"{reserve0:064x}" + f"{reserve1:064x}",
        "removed": False,
    }


def _domain(
    *addresses: str,
    start: int = BLOCK,
    end: int | None = None,
    topics: tuple[str, ...] = ORDERED_EVENT_TOPICS,
) -> QueryDomain:
    return QueryDomain(
        start_block=start,
        end_block=end if end is not None else PINNED_FINALITY_CUTOFF_BLOCK,
        addresses=tuple(sorted(addresses)),
        topics=topics,
    )


def _pool(address: str = POOL_A, creation: int = BLOCK) -> RegistryPoolBirth:
    return RegistryPoolBirth(pool_address=address, creation_block=creation)


def _make_header(
    plan_id: str,
    *,
    block_number: int,
    block_hash: str = "0x" + "ab" * 32,
    primary_raw: str = "9",
    secondary_raw: str = "8",
    primary_acq: str = "7",
    secondary_acq: str = "6",
    timestamp: int = 1_600_000_000,
) -> CanonicalHeaderReceiptRecord:
    hid = compute_canonical_header_receipt_id(
        plan_id=plan_id,
        block_number=block_number,
        block_hash=block_hash,
        block_timestamp=timestamp,
        primary_provider_org="infura",
        secondary_provider_org="blockpi",
        primary_raw_object_id="raw_" + primary_raw * 64,
        secondary_raw_object_id="raw_" + secondary_raw * 64,
        primary_acquisition_id="acq_" + primary_acq * 32,
        secondary_acquisition_id="acq_" + secondary_acq * 32,
    )
    return CanonicalHeaderReceiptRecord(
        header_receipt_id=hid,
        plan_id=plan_id,
        block_number=block_number,
        block_hash=block_hash,
        block_timestamp=timestamp,
        primary_provider_org="infura",
        secondary_provider_org="blockpi",
        primary_raw_object_id="raw_" + primary_raw * 64,
        secondary_raw_object_id="raw_" + secondary_raw * 64,
        primary_acquisition_id="acq_" + primary_acq * 32,
        secondary_acquisition_id="acq_" + secondary_acq * 32,
    )


def _make_receipt(
    *,
    plan_id: str,
    domain: QueryDomain,
    headers: list[CanonicalHeaderReceiptRecord],
    digest: str = "a" * 64,
    log_count: int = 0,
    primary_raw: str = "1",
    secondary_raw: str = "2",
) -> LeafReceiptRecord:
    return make_leaf_receipt_record(
        plan_id=plan_id,
        domain=domain,
        log_identity_sha256=digest,
        primary_provider_org="infura",
        secondary_provider_org="blockpi",
        primary_logs_raw_object_id="raw_" + primary_raw * 64,
        secondary_logs_raw_object_id="raw_" + secondary_raw * 64,
        primary_logs_acquisition_id="acq_" + "3" * 32,
        secondary_logs_acquisition_id="acq_" + "4" * 32,
        log_count=log_count,
        canonical_header_receipt_ids=[h.header_receipt_id for h in headers],
    )


# ---------------------------------------------------------------------------
# Plan / cohorts
# ---------------------------------------------------------------------------


class TestPlanConfig:
    def test_default_stable(self) -> None:
        assert PlanConfig().plan_id() == PlanConfig().plan_id()
        assert PlanConfig().initial_cohort_size == DEFAULT_INITIAL_COHORT_SIZE

    def test_matrix_cohorts_allowed_and_identity_bearing(self) -> None:
        assert CANDIDATE_COHORT_SIZES == frozenset({1, 8, 32, 64, 128})
        ids = {
            PlanConfig(initial_cohort_size=n).plan_id()
            for n in sorted(CANDIDATE_COHORT_SIZES)
        }
        assert len(ids) == 5

    def test_rejects_bad_cohort_and_pins(self) -> None:
        with pytest.raises(PairEventV2Error, match="candidates"):
            PlanConfig(initial_cohort_size=16)
        with pytest.raises(PairEventV2Error, match="pinned accepted"):
            PlanConfig(registry_dataset_id="ds_" + "0" * 64)
        with pytest.raises(PairEventV2Error, match="cutoff"):
            PlanConfig(cutoff_block=1)

    def test_plan_record_rejects_column_disagreement(self) -> None:
        cfg = PlanConfig()
        good = plan_record_from_config(cfg)
        assert good.plan_id == cfg.plan_id()
        with pytest.raises(PairEventV2Error, match="initial_cohort_size column"):
            PlanRecord(
                plan_id=good.plan_id,
                registry_dataset_id=good.registry_dataset_id,
                identity_payload_json=good.identity_payload_json,
                event_provider_orgs_json=good.event_provider_orgs_json,
                metadata_provider_orgs_json=good.metadata_provider_orgs_json,
                root_block_size=good.root_block_size,
                initial_cohort_size=32,  # disagrees with payload (64)
                deployment_block=good.deployment_block,
                cutoff_block=good.cutoff_block,
            )
        with pytest.raises(PairEventV2Error, match="event_provider_orgs_json"):
            PlanRecord(
                plan_id=good.plan_id,
                registry_dataset_id=good.registry_dataset_id,
                identity_payload_json=good.identity_payload_json,
                event_provider_orgs_json='["alchemy","blockpi"]',
                metadata_provider_orgs_json=good.metadata_provider_orgs_json,
                root_block_size=good.root_block_size,
                initial_cohort_size=good.initial_cohort_size,
                deployment_block=good.deployment_block,
                cutoff_block=good.cutoff_block,
            )


# ---------------------------------------------------------------------------
# Domains / logs / splits
# ---------------------------------------------------------------------------


class TestFoundationBasics:
    def test_roots_and_domain(self) -> None:
        windows = iter_root_windows()
        assert windows[0][0] == 10_000_835
        assert windows[-1][1] == PINNED_FINALITY_CUTOFF_BLOCK
        with pytest.raises(PairEventV2Error, match="after plan cutoff"):
            sort_pool_births([_pool(POOL_A, PINNED_FINALITY_CUTOFF_BLOCK + 1)])
        with pytest.raises(PairEventV2Error, match="20-byte"):
            QueryDomain(start_block=BLOCK, end_block=BLOCK + 1, addresses=("x",))

    def test_request_shape(self) -> None:
        req = combined_pair_logs_request(
            addresses=[POOL_A, POOL_B], start_block=BLOCK, end_block=BLOCK + 9
        )
        assert req["params"][0]["topics"] == [list(ORDERED_EVENT_TOPICS)]

    def test_log_identity_and_shapes(self) -> None:
        domain = QueryDomain(start_block=BLOCK, end_block=BLOCK + 10, addresses=(POOL_A,))
        assert extract_log_identity_v2(_swap_log(tx_index=9)).tx_index == 9
        with pytest.raises(PairEventV2Error):
            normalize_and_index_logs([_swap_log(topics=[SWAP_TOPIC])], domain)
        with pytest.raises(PairEventV2Error, match="position"):
            normalize_and_index_logs(
                [_swap_log(), _swap_log(data="0x" + ("11" * 32) * 4)], domain
            )
        with pytest.raises(PairEventV2Error, match="identity disagreement"):
            reconcile_log_sets_v2([_swap_log(tx_index=1)], [_swap_log(tx_index=2)], domain)
        rows, digest = reconcile_log_sets_v2([_swap_log()], [_swap_log()], domain)
        assert digest == log_identity_v2_digest(rows)
        validate_event_shape(extract_log_identity_v2(_sync_log()))

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("address", POOL_B),
            ("blockNumber", hex(BLOCK + 1)),
            ("blockHash", "0x" + "bc" * 32),
            ("transactionHash", "0x" + "de" * 32),
            ("transactionIndex", hex(8)),
            ("logIndex", hex(4)),
            ("topics", [SWAP_TOPIC, _addr_topic(0x44), _addr_topic(0x33)]),
            ("data", "0x" + ("11" * 32) * 4),
            ("removed", True),
        ],
    )
    def test_secondary_only_identity_field_change_fails_closed(
        self, field: str, value: object
    ) -> None:
        domain = QueryDomain(
            start_block=BLOCK,
            end_block=BLOCK + 1,
            addresses=(POOL_A, POOL_B),
        )
        primary = _swap_log()
        secondary = dict(primary)
        secondary[field] = value
        with pytest.raises(PairEventV2Error):
            reconcile_log_sets_v2([primary], [secondary], domain)

    def test_splits(self) -> None:
        domain = QueryDomain(
            start_block=BLOCK,
            end_block=BLOCK + 99,
            addresses=tuple(sorted([POOL_A, POOL_B, POOL_C])),
        )
        validate_children_partition(domain, split_domain_by_address(domain))
        validate_children_partition(domain, split_domain_by_block(domain))
        node = QueryNode(plan_id=PlanConfig().plan_id(), domain=domain)
        kids = split_node(node, reason="oversized_result")
        assert all(k.parent_domain_id == node.domain_id for k in kids)

    def test_malformed_child_partitions_fail_closed(self) -> None:
        parent = QueryDomain(
            start_block=BLOCK,
            end_block=BLOCK + 9,
            addresses=(POOL_A, POOL_B),
        )
        with pytest.raises(PairEventV2Error, match="exact partition"):
            validate_children_partition(
                parent,
                [
                    QueryDomain(
                        start_block=BLOCK,
                        end_block=BLOCK + 9,
                        addresses=(POOL_A,),
                    )
                ],
            )
        with pytest.raises(PairEventV2Error, match="gap or overlap"):
            validate_children_partition(
                parent,
                [
                    QueryDomain(
                        start_block=BLOCK,
                        end_block=BLOCK + 3,
                        addresses=(POOL_A, POOL_B),
                    ),
                    QueryDomain(
                        start_block=BLOCK + 5,
                        end_block=BLOCK + 9,
                        addresses=(POOL_A, POOL_B),
                    ),
                ],
            )

    def test_filter_count_when_present(self) -> None:
        path = Path(
            "data/dex003_full/store/datasets/sha256/42/ce/"
            f"{ACCEPTED_DEX_POOL_REGISTRY_DATASET_ID}/"
            "dex/dex_pool_registry/pools.parquet"
        )
        if not path.is_file():
            pytest.skip("registry parquet absent")
        import pyarrow.parquet as pq

        t = pq.read_table(path, columns=["pool_address", "creation_block"])
        pools = sort_pool_births(
            [
                RegistryPoolBirth(pool_address=str(a), creation_block=int(c))
                for a, c in zip(
                    t.column("pool_address").to_pylist(),
                    t.column("creation_block").to_pylist(),
                )
            ]
        )
        n = 0
        for _s, e in iter_root_windows():
            addrs = [p.pool_address for p in pools if p.creation_block <= e]
            if addrs:
                n += (len(addrs) + 63) // 64
        assert n == 233_694


# ---------------------------------------------------------------------------
# Coverage authority
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_complete_with_matching_header(self) -> None:
        plan_id = PlanConfig().plan_id()
        domain = _domain(POOL_A)
        header = _make_header(plan_id, block_number=domain.end_block)
        receipt = _make_receipt(plan_id=plan_id, domain=domain, headers=[header])
        cov = prove_pool_topic_coverage(
            _pool(POOL_A),
            plan_id=plan_id,
            topic=SWAP_TOPIC,
            validated_receipts=[receipt],
            validated_headers=[header],
        )
        assert cov.is_complete
        assert not cov.has_gap and not cov.has_overlap
        assert cov.leaf_count == 1

    def test_missing_header_record_fails_closed(self) -> None:
        plan_id = PlanConfig().plan_id()
        domain = _domain(POOL_A)
        header = _make_header(plan_id, block_number=domain.end_block)
        receipt = _make_receipt(plan_id=plan_id, domain=domain, headers=[header])
        with pytest.raises(PairEventV2Error, match="missing canonical header"):
            prove_pool_topic_coverage(
                _pool(POOL_A),
                plan_id=plan_id,
                topic=SWAP_TOPIC,
                validated_receipts=[receipt],
                validated_headers=[],  # no header map
            )

    def test_header_without_boundary_fails(self) -> None:
        plan_id = PlanConfig().plan_id()
        domain = _domain(POOL_A)
        # Header for a different block than end_block.
        wrong = _make_header(plan_id, block_number=domain.start_block)
        # Force leaf to reference wrong header only: build id with wrong boundary.
        with pytest.raises(PairEventV2Error, match="end-block boundary"):
            # Create receipt that lists only start-block header — ID will bind it,
            # then coverage must reject for missing end-block header evidence.
            receipt = _make_receipt(plan_id=plan_id, domain=domain, headers=[wrong])
            prove_pool_topic_coverage(
                _pool(POOL_A),
                plan_id=plan_id,
                topic=SWAP_TOPIC,
                validated_receipts=[receipt],
                validated_headers=[wrong],
            )

    def test_header_provider_mismatch_fails(self) -> None:
        plan_id = PlanConfig().plan_id()
        domain = _domain(POOL_A)
        # Header with different secondary org can't be used with infura/blockpi leaf.
        hid = compute_canonical_header_receipt_id(
            plan_id=plan_id,
            block_number=domain.end_block,
            block_hash="0x" + "ab" * 32,
            block_timestamp=1,
            primary_provider_org="infura",
            secondary_provider_org="alchemy",
            primary_raw_object_id="raw_" + "1" * 64,
            secondary_raw_object_id="raw_" + "2" * 64,
            primary_acquisition_id="acq_" + "3" * 32,
            secondary_acquisition_id="acq_" + "4" * 32,
        )
        header = CanonicalHeaderReceiptRecord(
            header_receipt_id=hid,
            plan_id=plan_id,
            block_number=domain.end_block,
            block_hash="0x" + "ab" * 32,
            block_timestamp=1,
            primary_provider_org="infura",
            secondary_provider_org="alchemy",
            primary_raw_object_id="raw_" + "1" * 64,
            secondary_raw_object_id="raw_" + "2" * 64,
            primary_acquisition_id="acq_" + "3" * 32,
            secondary_acquisition_id="acq_" + "4" * 32,
        )
        receipt = make_leaf_receipt_record(
            plan_id=plan_id,
            domain=domain,
            log_identity_sha256="a" * 64,
            primary_provider_org="infura",
            secondary_provider_org="blockpi",
            primary_logs_raw_object_id="raw_" + "a" * 64,
            secondary_logs_raw_object_id="raw_" + "b" * 64,
            primary_logs_acquisition_id="acq_" + "c" * 32,
            secondary_logs_acquisition_id="acq_" + "d" * 32,
            log_count=0,
            canonical_header_receipt_ids=[hid],
        )
        with pytest.raises(PairEventV2Error, match="provider_org"):
            prove_pool_topic_coverage(
                _pool(POOL_A),
                plan_id=plan_id,
                topic=SWAP_TOPIC,
                validated_receipts=[receipt],
                validated_headers=[header],
            )

    def test_leaf_id_binds_header_set(self) -> None:
        plan_id = PlanConfig().plan_id()
        domain = _domain(POOL_A)
        h1 = _make_header(plan_id, block_number=domain.end_block, primary_raw="1")
        h2 = _make_header(
            plan_id,
            block_number=domain.end_block,
            block_hash="0x" + "cd" * 32,
            primary_raw="3",
            secondary_raw="4",
            timestamp=2,
        )
        base = dict(
            plan_id=plan_id,
            domain_id=domain.domain_id(plan_id),
            start_block=domain.start_block,
            end_block=domain.end_block,
            addresses=domain.addresses,
            topics=domain.topics,
            log_identity_sha256="a" * 64,
            primary_provider_org="infura",
            secondary_provider_org="blockpi",
            primary_logs_raw_object_id="raw_" + "a" * 64,
            secondary_logs_raw_object_id="raw_" + "b" * 64,
            primary_logs_acquisition_id="acq_" + "c" * 32,
            secondary_logs_acquisition_id="acq_" + "d" * 32,
            log_count=0,
        )
        id1 = compute_leaf_receipt_id(
            **base, canonical_header_receipt_ids=[h1.header_receipt_id]
        )
        id2 = compute_leaf_receipt_id(
            **base,
            canonical_header_receipt_ids=[
                h1.header_receipt_id,
                h2.header_receipt_id,
            ],
        )
        assert id1 != id2

    def test_partial_gap_flag(self) -> None:
        plan_id = PlanConfig().plan_id()
        domain = QueryDomain(
            start_block=BLOCK, end_block=BLOCK + 1000, addresses=(POOL_A,)
        )
        header = _make_header(plan_id, block_number=domain.end_block)
        receipt = _make_receipt(plan_id=plan_id, domain=domain, headers=[header])
        cov = prove_pool_topic_coverage(
            _pool(POOL_A),
            plan_id=plan_id,
            topic=SWAP_TOPIC,
            validated_receipts=[receipt],
            validated_headers=[header],
        )
        assert not cov.is_complete
        assert cov.has_gap

    def test_mixed_plan_receipt_and_header_fail_closed(self) -> None:
        plan_a = PlanConfig().plan_id()
        plan_b = PlanConfig(initial_cohort_size=32).plan_id()
        domain = _domain(POOL_A, end=BLOCK + 10)
        header_b = _make_header(plan_b, block_number=domain.end_block)
        receipt_b = _make_receipt(plan_id=plan_b, domain=domain, headers=[header_b])
        with pytest.raises(PairEventV2Error, match="receipt plan_id"):
            prove_pool_topic_coverage(
                _pool(POOL_A),
                plan_id=plan_a,
                topic=SWAP_TOPIC,
                validated_receipts=[receipt_b],
                validated_headers=[header_b],
                cutoff_block=BLOCK + 10,
            )

        receipt_a = _make_receipt(plan_id=plan_a, domain=domain, headers=[header_b])
        with pytest.raises(PairEventV2Error, match="plan_id"):
            prove_pool_topic_coverage(
                _pool(POOL_A),
                plan_id=plan_a,
                topic=SWAP_TOPIC,
                validated_receipts=[receipt_a],
                validated_headers=[header_b],
                cutoff_block=BLOCK + 10,
            )

    def test_overlapping_coverage_is_incomplete(self) -> None:
        plan_id = PlanConfig().plan_id()
        first = _domain(POOL_A, end=BLOCK + 10)
        second = _domain(POOL_A, start=BLOCK + 10, end=BLOCK + 20)
        h1 = _make_header(plan_id, block_number=first.end_block)
        h2 = _make_header(plan_id, block_number=second.end_block)
        cov = prove_pool_topic_coverage(
            _pool(POOL_A),
            plan_id=plan_id,
            topic=SWAP_TOPIC,
            validated_receipts=[
                _make_receipt(plan_id=plan_id, domain=second, headers=[h2]),
                _make_receipt(plan_id=plan_id, domain=first, headers=[h1]),
            ],
            validated_headers=[h1, h2],
            cutoff_block=BLOCK + 20,
        )
        assert cov.has_overlap
        assert not cov.is_complete

    def test_receipt_root_is_deterministic_under_input_reordering(self) -> None:
        plan_id = PlanConfig().plan_id()
        first = _domain(POOL_A, end=BLOCK + 9)
        second = _domain(POOL_A, start=BLOCK + 10, end=BLOCK + 20)
        h1 = _make_header(plan_id, block_number=first.end_block)
        h2 = _make_header(plan_id, block_number=second.end_block)
        r1 = _make_receipt(plan_id=plan_id, domain=first, headers=[h1])
        r2 = _make_receipt(plan_id=plan_id, domain=second, headers=[h2])
        forward = prove_pool_topic_coverage(
            _pool(POOL_A),
            plan_id=plan_id,
            topic=SWAP_TOPIC,
            validated_receipts=[r1, r2],
            validated_headers=[h1, h2],
            cutoff_block=BLOCK + 20,
        )
        reverse = prove_pool_topic_coverage(
            _pool(POOL_A),
            plan_id=plan_id,
            topic=SWAP_TOPIC,
            validated_receipts=[r2, r1],
            validated_headers=[h2, h1],
            cutoff_block=BLOCK + 20,
        )
        assert forward.supporting_receipts_root == reverse.supporting_receipts_root
        assert forward.coverage_hash == reverse.coverage_hash

    def test_large_synthetic_stream_keeps_one_report_per_pool_topic(self) -> None:
        plan_id = PlanConfig().plan_id()
        end = BLOCK + 255
        receipts = []
        headers = []
        for block in range(BLOCK, end + 1):
            domain = _domain(POOL_A, start=block, end=block)
            header = _make_header(plan_id, block_number=block)
            headers.append(header)
            receipts.append(_make_receipt(plan_id=plan_id, domain=domain, headers=[header]))
        reports = prove_full_registry_coverage(
            [_pool(POOL_A)],
            plan_id=plan_id,
            validated_receipts=receipts,
            validated_headers=headers,
            cutoff_block=end,
        )
        assert len(reports) == len(ORDERED_EVENT_TOPICS)
        assert all(report.is_complete and report.leaf_count == 256 for report in reports)

    def test_full_registry_streaming(self) -> None:
        plan_id = PlanConfig().plan_id()
        domain = _domain(POOL_A)
        header = _make_header(plan_id, block_number=domain.end_block)
        receipt = _make_receipt(plan_id=plan_id, domain=domain, headers=[header])
        reports = prove_full_registry_coverage(
            [_pool(POOL_A), _pool(POOL_B)],
            plan_id=plan_id,
            validated_receipts=[receipt],
            validated_headers=[header],
        )
        assert len(reports) == 4
        assert any(r.pool_address == POOL_A and r.is_complete for r in reports)
        assert all(not r.is_complete for r in reports if r.pool_address == POOL_B)

    def test_forged_leaf_id_rejected(self) -> None:
        plan_id = PlanConfig().plan_id()
        domain = _domain(POOL_A)
        header = _make_header(plan_id, block_number=domain.end_block)
        with pytest.raises(PairEventV2Error, match="deterministic content identity"):
            LeafReceiptRecord(
                leaf_receipt_id="leaf_" + "0" * 64,
                plan_id=plan_id,
                domain_id=domain.domain_id(plan_id),
                start_block=domain.start_block,
                end_block=domain.end_block,
                addresses=domain.addresses,
                topics=domain.topics,
                primary_provider_org="infura",
                secondary_provider_org="blockpi",
                primary_logs_raw_object_id="raw_" + "1" * 64,
                secondary_logs_raw_object_id="raw_" + "2" * 64,
                primary_logs_acquisition_id="acq_" + "3" * 32,
                secondary_logs_acquisition_id="acq_" + "4" * 32,
                log_count=0,
                log_identity_sha256="a" * 64,
                canonical_header_receipt_ids=(header.header_receipt_id,),
            )


class TestPlanBuild:
    def test_small_plan(self) -> None:
        plan = build_acquisition_plan_v2([_pool(POOL_A), _pool(POOL_B, BLOCK + 5000)])
        assert plan.root_filter_count > 0
        assert plan.plan_id == PlanConfig().plan_id()
