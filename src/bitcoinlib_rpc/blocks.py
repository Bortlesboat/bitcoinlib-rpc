"""Block analysis: mining pool detection, script adoption, fee distribution."""

from __future__ import annotations

import statistics
import sys
from datetime import datetime, timezone

from bitcoinlib_rpc.rpc import BitcoinRPC
from bitcoinlib_rpc.types import BlockAnalysis
from bitcoinlib_rpc.utils import (
    btc_to_sats,
    calc_fee_rate,
    detect_script_type,
    format_btc,
    identify_pool,
)

MAX_BLOCK_WEIGHT = 4_000_000


def analyze_block(rpc: BitcoinRPC, height_or_hash: int | str) -> BlockAnalysis:
    """Analyze a block by height or hash."""
    if isinstance(height_or_hash, int) or height_or_hash.isdigit():
        blockhash = rpc.getblockhash(int(height_or_hash))
    else:
        blockhash = height_or_hash

    block = rpc.getblock(blockhash, verbosity=2)

    # Parse coinbase for pool identification
    coinbase_tx = block["tx"][0]
    coinbase_hex = coinbase_tx["vin"][0].get("coinbase", "")
    pool_name = identify_pool(coinbase_hex)

    # Subsidy from coinbase output
    subsidy_btc = sum(vout["value"] for vout in coinbase_tx["vout"])

    # Analyze all non-coinbase transactions
    segwit_count = 0
    taproot_count = 0
    fee_rates: list[float] = []
    tx_fees: list[tuple[str, float]] = []  # (txid, fee_rate)

    for tx in block["tx"][1:]:
        is_segwit = any(vin.get("txinwitness") for vin in tx.get("vin", []))
        if is_segwit:
            segwit_count += 1

        is_taproot = any(
            detect_script_type(vout["scriptPubKey"]) == "P2TR"
            for vout in tx.get("vout", [])
        )
        if is_taproot:
            taproot_count += 1

        # Fee rate from block stats if available, otherwise estimate
        vsize = tx.get("vsize", tx["size"])
        # We can't easily calculate individual fees without resolving inputs
        # Use weight-based estimate from block's fee data
        if "fee" in tx:
            fee_sats = btc_to_sats(tx["fee"])
            rate = calc_fee_rate(fee_sats, vsize)
            fee_rates.append(rate)
            tx_fees.append((tx["txid"], rate))

    # If individual fees weren't available, try blockstats
    total_fee_btc = 0.0
    if not fee_rates:
        try:
            stats = rpc.getblockstats(block["height"])
            total_fee_btc = stats["totalfee"] / 1e8
            if stats.get("minfeerate") is not None:
                fee_rates = [
                    stats.get("minfeerate", 0),
                    stats.get("medianfee", 0) / max(stats.get("mediantxsize", 1), 1),
                    stats.get("maxfeerate", 0),
                ]
        except Exception:
            pass
    else:
        total_fee_btc = sum(r * 1 for r in fee_rates) / 1e8  # rough estimate

    # Calculate from coinbase: total revenue - subsidy = fees
    coinbase_value = sum(vout["value"] for vout in coinbase_tx["vout"])
    # Block subsidy at current halving
    height = block["height"]
    halvings = height // 210_000
    block_subsidy = 50.0 / (2 ** halvings)
    total_fee_btc = coinbase_value - block_subsidy
    if total_fee_btc < 0:
        total_fee_btc = 0.0

    tx_count = len(block["tx"])
    non_cb = max(tx_count - 1, 1)

    top_fee = sorted(tx_fees, key=lambda x: x[1], reverse=True)[:5]

    return BlockAnalysis(
        height=block["height"],
        hash=block["hash"],
        timestamp=datetime.fromtimestamp(block["time"], tz=timezone.utc),
        version=block["version"],
        size=block["size"],
        weight=block["weight"],
        tx_count=tx_count,
        pool_name=pool_name,
        subsidy_btc=block_subsidy,
        total_fee_btc=total_fee_btc,
        total_revenue_btc=block_subsidy + total_fee_btc,
        weight_utilization_pct=(block["weight"] / MAX_BLOCK_WEIGHT) * 100,
        segwit_tx_count=segwit_count,
        taproot_tx_count=taproot_count,
        segwit_pct=(segwit_count / non_cb) * 100 if non_cb else 0,
        taproot_pct=(taproot_count / non_cb) * 100 if non_cb else 0,
        fee_rate_min=min(fee_rates) if fee_rates else 0,
        fee_rate_median=statistics.median(fee_rates) if fee_rates else 0,
        fee_rate_max=max(fee_rates) if fee_rates else 0,
        top_fee_txids=[(txid, rate) for txid, rate in top_fee],
    )


def print_block(analysis: BlockAnalysis) -> None:
    """Print block analysis to terminal."""
    print(f"{'BLOCK ANALYSIS':=^60}")
    print(f"{'Height:':<20} {analysis.height:,}")
    print(f"{'Hash:':<20} {analysis.hash}")
    print(f"{'Timestamp:':<20} {analysis.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'Miner pool:':<20} {analysis.pool_name}")
    print()
    print(f"{'Size:':<20} {analysis.size:,} bytes")
    print(f"{'Weight:':<20} {analysis.weight:,} WU ({analysis.weight_utilization_pct:.1f}%)")
    print(f"{'Transactions:':<20} {analysis.tx_count:,}")
    print()
    print(f"{'ADOPTION':=^60}")
    print(f"{'SegWit txs:':<20} {analysis.segwit_tx_count:,} ({analysis.segwit_pct:.1f}%)")
    print(f"{'Taproot txs:':<20} {analysis.taproot_tx_count:,} ({analysis.taproot_pct:.1f}%)")
    print()
    print(f"{'MINING REVENUE':=^60}")
    print(f"{'Subsidy:':<20} {format_btc(analysis.subsidy_btc)}")
    print(f"{'Fees:':<20} {format_btc(analysis.total_fee_btc)}")
    print(f"{'Total revenue:':<20} {format_btc(analysis.total_revenue_btc)}")

    if analysis.fee_rate_min > 0:
        print()
        print(f"{'FEE RATES':=^60}")
        print(f"{'Min:':<20} {analysis.fee_rate_min:.1f} sat/vB")
        print(f"{'Median:':<20} {analysis.fee_rate_median:.1f} sat/vB")
        print(f"{'Max:':<20} {analysis.fee_rate_max:.1f} sat/vB")

    if analysis.top_fee_txids:
        print()
        print(f"{'TOP FEE TRANSACTIONS':=^60}")
        for i, (txid, rate) in enumerate(analysis.top_fee_txids):
            print(f"  [{i}] {txid[:16]}... → {rate:.1f} sat/vB")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: bitcoin-block <height|hash>", file=sys.stderr)
        sys.exit(1)

    target = sys.argv[1]
    try:
        rpc = BitcoinRPC()
        analysis = analyze_block(rpc, target)
        print_block(analysis)
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
