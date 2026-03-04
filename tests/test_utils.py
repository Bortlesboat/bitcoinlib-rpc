"""Tests for utility functions (no node required)."""

from bitcoinlib_rpc.utils import (
    btc_to_sats,
    calc_fee_rate,
    congestion_level,
    detect_script_type,
    fee_recommendation,
    format_btc,
    format_sats,
    format_size,
    identify_pool,
    sats_to_btc,
)


def test_sats_btc_conversion():
    assert sats_to_btc(100_000_000) == 1.0
    assert sats_to_btc(50_000) == 0.0005
    assert btc_to_sats(1.0) == 100_000_000
    assert btc_to_sats(0.00000001) == 1


def test_format_btc():
    assert format_btc(1.0) == "1.00000000 BTC"
    assert format_btc(0.5, decimals=4) == "0.5000 BTC"


def test_format_sats():
    assert format_sats(100_000) == "100,000 sats"
    assert format_sats(1) == "1 sats"


def test_format_size():
    assert format_size(500) == "500 bytes"
    assert format_size(1_500) == "1.5 KB"
    assert format_size(2_500_000) == "2.5 MB"
    assert format_size(1_500_000_000) == "1.5 GB"


def test_calc_fee_rate():
    assert calc_fee_rate(1000, 100) == 10.0
    assert calc_fee_rate(0, 100) == 0.0
    assert calc_fee_rate(100, 0) == 0.0


def test_detect_script_type():
    assert detect_script_type({"type": "witness_v1_taproot"}) == "P2TR"
    assert detect_script_type({"type": "pubkeyhash"}) == "P2PKH"
    assert detect_script_type({"type": "witness_v0_keyhash"}) == "P2WPKH"
    assert detect_script_type({"type": "nulldata"}) == "OP_RETURN"
    assert detect_script_type({"type": "unknown_type"}) == "unknown_type"


def test_identify_pool():
    assert identify_pool("", "Foundry USA Pool") == "Foundry USA"
    assert identify_pool("", "mined by AntPool") == "AntPool"
    assert identify_pool("", "some random coinbase") == "Unknown"


def test_congestion_level():
    assert congestion_level(100, 1_000_000) == "low"
    assert congestion_level(1000, 10_000_000) == "moderate"
    assert congestion_level(10000, 50_000_000) == "high"
    assert congestion_level(100000, 200_000_000) == "extreme"


def test_fee_recommendation():
    low = {1: 3.0, 3: 2.0, 6: 1.5, 25: 1.0, 144: 1.0}
    assert "very low" in fee_recommendation(low)

    high = {1: 50.0, 3: 40.0, 6: 30.0, 25: 15.0, 144: 5.0}
    assert "High fees" in fee_recommendation(high)

    extreme = {1: 200.0, 3: 150.0, 6: 100.0, 25: 50.0, 144: 20.0}
    assert "Extreme" in fee_recommendation(extreme)
