"""Tests for Pydantic models."""

from bitcoinlib_rpc.types import (
    BlockAnalysis,
    FeeEstimate,
    MempoolSummary,
    NodeStatus,
    TransactionAnalysis,
    TransactionOutput,
)


def test_node_status_synced():
    status = NodeStatus(
        chain="main",
        blocks=939290,
        headers=939290,
        verification_progress=1.0,
        size_on_disk=700_000_000_000,
        pruned=False,
        connections=10,
        version=270000,
        subversion="/Bitcoin Knots:27.1/",
    )
    assert status.synced is True
    assert status.size_on_disk_gb == 700.0


def test_node_status_not_synced():
    status = NodeStatus(
        chain="main",
        blocks=500000,
        headers=939290,
        verification_progress=0.5,
        size_on_disk=100_000_000_000,
        pruned=False,
        connections=8,
        version=270000,
        subversion="/Bitcoin Core:27.0/",
    )
    assert status.synced is False


def test_fee_estimate_from_rpc():
    est = FeeEstimate.from_rpc(6, {"feerate": 0.00025, "blocks": 6})
    assert est.conf_target == 6
    assert est.fee_rate_sat_vb == 25.0
    assert est.errors == []


def test_fee_estimate_with_errors():
    est = FeeEstimate.from_rpc(1, {"errors": ["Insufficient data"]})
    assert est.fee_rate_sat_vb == 0.0
    assert est.errors == ["Insufficient data"]


def test_transaction_analysis_discount():
    tx = TransactionAnalysis(
        txid="abc123",
        version=2,
        size=250,
        vsize=175,
        weight=700,
        locktime=0,
    )
    # Legacy would be 250*4=1000 WU, actual is 700 WU = 30% saving
    assert abs(tx.segwit_discount_pct - 30.0) < 0.1


def test_transaction_output_total():
    tx = TransactionAnalysis(
        txid="abc123",
        version=2,
        size=250,
        vsize=250,
        weight=1000,
        locktime=0,
        outputs=[
            TransactionOutput(index=0, value_btc=0.5, value_sats=50000000, script_type="P2WPKH"),
            TransactionOutput(index=1, value_btc=0.3, value_sats=30000000, script_type="P2WPKH"),
        ],
    )
    assert tx.total_output_btc == 0.8
