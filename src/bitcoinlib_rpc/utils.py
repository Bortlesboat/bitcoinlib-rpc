"""Shared utilities for Bitcoin analysis."""

from __future__ import annotations

import re
from typing import Optional

# Known mining pool coinbase signatures
POOL_IDENTIFIERS: dict[str, list[str]] = {
    "Foundry USA": ["Foundry USA Pool", "Foundry"],
    "AntPool": ["Antpool", "AntPool", "antpool.com"],
    "ViaBTC": ["ViaBTC", "viabtc.com"],
    "F2Pool": ["F2Pool", "/f2pool/", "🐟"],
    "Binance Pool": ["Binance", "binance.com"],
    "MARA Pool": ["MARA Pool", "MARA", "Marathon"],
    "Luxor": ["Luxor", "luxor.tech"],
    "Braiins Pool": ["Braiins", "slushpool", "braiins.com"],
    "SBI Crypto": ["SBI Crypto"],
    "OCEAN": ["OCEAN", "ocean.xyz"],
    "SpiderPool": ["SpiderPool", "spiderpool.com"],
    "Poolin": ["Poolin", "poolin.com"],
    "BTC.com": ["BTC.com", "btc.com"],
    "Titan": ["Titan"],
    "Bitdeer": ["Bitdeer", "bitdeer.com"],
    "CleanSpark": ["CleanSpark"],
    "DEMAND": ["DEMAND", "demand.io"],
    "SecPool": ["SecPool", "secpool.com"],
    "WhitePool": ["WhitePool"],
    "Ultimus Pool": ["Ultimus", "ultimuspool"],
    "PEGA Pool": ["PEGA Pool", "PEGA"],
    "Loka Mining": ["Loka"],
    "Carbon Negative": ["Carbon Negative"],
    "Rawpool": ["Rawpool", "rawpool.com"],
    "EMCDPool": ["EMCD", "emcd.io"],
    "1THash": ["1THash", "1thash.top"],
    "KuCoin Pool": ["KuCoin"],
    "Solo CKPool": ["solo.ckpool", "ckpool"],
}


def sats_to_btc(sats: int) -> float:
    """Convert satoshis to BTC."""
    return sats / 100_000_000


def btc_to_sats(btc: float) -> int:
    """Convert BTC to satoshis."""
    return int(round(btc * 100_000_000))


def format_btc(btc: float, decimals: int = 8) -> str:
    """Format BTC value for display."""
    return f"{btc:.{decimals}f} BTC"


def format_sats(sats: int) -> str:
    """Format satoshis with comma separator."""
    return f"{sats:,} sats"


def format_size(bytes_val: int) -> str:
    """Format bytes as human-readable size."""
    if bytes_val >= 1_000_000_000:
        return f"{bytes_val / 1e9:.1f} GB"
    if bytes_val >= 1_000_000:
        return f"{bytes_val / 1e6:.1f} MB"
    if bytes_val >= 1_000:
        return f"{bytes_val / 1e3:.1f} KB"
    return f"{bytes_val} bytes"


def calc_fee_rate(fee_sats: int, vsize: int) -> float:
    """Calculate fee rate in sat/vB."""
    if vsize == 0:
        return 0.0
    return fee_sats / vsize


def detect_script_type(script_pubkey: dict) -> str:
    """Identify the script type from a scriptPubKey dict."""
    stype = script_pubkey.get("type", "unknown")
    mapping = {
        "pubkeyhash": "P2PKH",
        "scripthash": "P2SH",
        "witness_v0_keyhash": "P2WPKH",
        "witness_v0_scripthash": "P2WSH",
        "witness_v1_taproot": "P2TR",
        "pubkey": "P2PK",
        "multisig": "Bare Multisig",
        "nulldata": "OP_RETURN",
        "nonstandard": "Non-standard",
    }
    return mapping.get(stype, stype)


def extract_address(script_pubkey: dict) -> Optional[str]:
    """Extract address from scriptPubKey if available."""
    return script_pubkey.get("address")


def detect_inscription(witness: list[str]) -> tuple[bool, Optional[str]]:
    """Check witness data for Ordinals inscription.

    Returns (has_inscription, content_type).
    """
    for item in witness:
        # Look for the ord envelope marker
        # "ord" in hex = 6f7264
        if "6f7264" in item:
            # Try to extract content type
            # Content type follows the 01 tag after ord marker
            content_type = _extract_inscription_content_type(item)
            return True, content_type
    return False, None


def _extract_inscription_content_type(hex_data: str) -> Optional[str]:
    """Try to extract MIME type from inscription envelope."""
    try:
        # Find ord marker, then look for content type tag (01)
        idx = hex_data.index("6f7264")
        # After "ord" (6f7264), expect 01 (content type tag)
        remaining = hex_data[idx + 6 :]
        if remaining.startswith("01"):
            # Next bytes should be pushdata with MIME type
            remaining = remaining[2:]
            # Try to decode as ASCII
            ascii_bytes = bytes.fromhex(remaining[:200])
            # Find printable ASCII run
            text = ""
            for b in ascii_bytes:
                if 32 <= b < 127:
                    text += chr(b)
                elif text:
                    break
            if "/" in text:
                return text.strip()
    except (ValueError, IndexError):
        pass
    return None


def identify_pool(coinbase_hex: str, coinbase_text: str = "") -> str:
    """Identify mining pool from coinbase transaction data."""
    # Try text first
    if not coinbase_text:
        try:
            coinbase_text = bytes.fromhex(coinbase_hex).decode("utf-8", errors="replace")
        except (ValueError, UnicodeDecodeError):
            coinbase_text = ""

    for pool_name, signatures in POOL_IDENTIFIERS.items():
        for sig in signatures:
            if sig.lower() in coinbase_text.lower():
                return pool_name

    return "Unknown"


def congestion_level(mempool_size: int, mempool_bytes: int) -> str:
    """Assess mempool congestion."""
    mb = mempool_bytes / 1_000_000
    if mb < 5:
        return "low"
    if mb < 20:
        return "moderate"
    if mb < 100:
        return "high"
    return "extreme"


def fee_recommendation(fee_estimates: dict[int, float]) -> str:
    """Generate plain-English fee recommendation."""
    next_block = fee_estimates.get(1, 0)
    half_hour = fee_estimates.get(3, 0)
    hour = fee_estimates.get(6, 0)
    day = fee_estimates.get(144, 0)

    if next_block < 5:
        return f"Fees are very low. {day:.1f} sat/vB should confirm within a day."
    if next_block < 20:
        return (
            f"Moderate fees. Use {half_hour:.1f} sat/vB for ~30 min, "
            f"or {day:.1f} sat/vB if you can wait."
        )
    if next_block < 100:
        return (
            f"High fees ({next_block:.1f} sat/vB for next block). "
            f"Consider waiting — {day:.1f} sat/vB should confirm in ~24h."
        )
    return (
        f"Extreme fees ({next_block:.1f} sat/vB). "
        "Delay non-urgent transactions if possible."
    )
