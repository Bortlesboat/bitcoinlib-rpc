"""Mempool analysis with fee distribution bucketing."""

from __future__ import annotations

import sys
from datetime import datetime

from bitcoinlib_rpc.rpc import BitcoinRPC
from bitcoinlib_rpc.types import FeeBucket, MempoolSummary
from bitcoinlib_rpc.utils import congestion_level, format_size

# Fee rate buckets in sat/vB
BUCKET_RANGES = [
    (1, 2, "1-2 sat/vB"),
    (2, 5, "2-5 sat/vB"),
    (5, 10, "5-10 sat/vB"),
    (10, 20, "10-20 sat/vB"),
    (20, 50, "20-50 sat/vB"),
    (50, 100, "50-100 sat/vB"),
    (100, 500, "100-500 sat/vB"),
    (500, float("inf"), "500+ sat/vB"),
]

# Next block weight limit
MAX_BLOCK_WEIGHT = 4_000_000


def analyze_mempool(rpc: BitcoinRPC) -> MempoolSummary:
    """Analyze the current mempool and return a typed summary."""
    info = rpc.getmempoolinfo()
    raw = rpc.getrawmempool(verbose=True)

    buckets = [
        FeeBucket(min_rate=lo, max_rate=hi, label=label)
        for lo, hi, label in BUCKET_RANGES
    ]

    # Sort txs by fee rate descending to find next-block cutoff
    fee_rates: list[tuple[float, int]] = []  # (fee_rate, weight)

    for txid, entry in raw.items():
        vsize = entry.get("vsize", entry.get("size", 0))
        fee_btc = entry.get("fees", {}).get("base", entry.get("fee", 0))
        fee_sats = int(round(fee_btc * 1e8))
        weight = entry.get("weight", vsize * 4)

        if vsize == 0:
            continue

        rate = fee_sats / vsize
        fee_rates.append((rate, weight))

        for bucket in buckets:
            if bucket.min_rate <= rate < bucket.max_rate:
                bucket.count += 1
                bucket.total_vsize += vsize
                break

    # Find minimum fee rate to enter next block
    fee_rates.sort(key=lambda x: x[0], reverse=True)
    cumulative_weight = 0
    next_block_min = 0.0
    for rate, weight in fee_rates:
        cumulative_weight += weight
        if cumulative_weight >= MAX_BLOCK_WEIGHT:
            next_block_min = rate
            break

    total_fee = sum(
        entry.get("fees", {}).get("base", entry.get("fee", 0))
        for entry in raw.values()
    )

    cong = congestion_level(info["size"], info["bytes"])

    return MempoolSummary(
        size=info["size"],
        total_bytes=info["bytes"],
        total_fee_btc=total_fee,
        min_relay_fee=info.get("minrelaytxfee", 0.00001),
        buckets=buckets,
        next_block_min_fee=next_block_min,
        congestion=cong,
        timestamp=datetime.now(),
    )


def print_mempool(summary: MempoolSummary) -> None:
    """Print mempool analysis to terminal."""
    print(f"{'MEMPOOL SNAPSHOT':=^60}")
    print(f"{'Transactions:':<25} {summary.size:,}")
    print(f"{'Total size:':<25} {format_size(summary.total_bytes)}")
    print(f"{'Total fees:':<25} {summary.total_fee_btc:.8f} BTC")
    print(f"{'Congestion:':<25} {summary.congestion.upper()}")
    print(f"{'Next block min fee:':<25} {summary.next_block_min_fee:.1f} sat/vB")
    print()
    print(f"{'FEE DISTRIBUTION':=^60}")
    print(f"{'Bucket':<20} {'Count':>8} {'Total vSize':>15}")
    print("-" * 60)
    for b in summary.buckets:
        if b.count > 0:
            print(f"{b.label:<20} {b.count:>8,} {format_size(b.total_vsize):>15}")


def main() -> None:
    try:
        rpc = BitcoinRPC()
        summary = analyze_mempool(rpc)
        print_mempool(summary)
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
