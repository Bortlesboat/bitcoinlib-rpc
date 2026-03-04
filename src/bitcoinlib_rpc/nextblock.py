"""Next block prediction from getblocktemplate."""

from __future__ import annotations

import statistics
import sys

from bitcoinlib_rpc.rpc import BitcoinRPC
from bitcoinlib_rpc.utils import format_btc, format_sats

MAX_BLOCK_WEIGHT = 4_000_000


def analyze_next_block(rpc: BitcoinRPC) -> dict:
    """Analyze the current block template."""
    template = rpc.getblocktemplate()

    height = template["height"]
    halvings = height // 210_000
    subsidy_sats = int(50 * 1e8) >> halvings

    txs = template.get("transactions", [])
    total_fee_sats = sum(tx.get("fee", 0) for tx in txs)
    total_weight = sum(tx.get("weight", 0) for tx in txs)

    fee_rates: list[float] = []
    tx_fees: list[tuple[str, float, int]] = []  # (txid, rate, fee)

    for tx in txs:
        weight = tx.get("weight", 0)
        fee = tx.get("fee", 0)
        if weight > 0:
            vsize = (weight + 3) // 4  # ceil division
            rate = fee / vsize
            fee_rates.append(rate)
            tx_fees.append((tx.get("txid", tx.get("hash", "?")), rate, fee))

    tx_fees.sort(key=lambda x: x[1], reverse=True)

    result = {
        "height": height,
        "tx_count": len(txs),
        "total_weight": total_weight,
        "weight_pct": (total_weight / MAX_BLOCK_WEIGHT) * 100,
        "subsidy_sats": subsidy_sats,
        "total_fee_sats": total_fee_sats,
        "total_revenue_sats": subsidy_sats + total_fee_sats,
        "fee_rates": fee_rates,
        "top_5": tx_fees[:5],
    }

    if fee_rates:
        fee_rates_sorted = sorted(fee_rates)
        n = len(fee_rates_sorted)
        result["fee_min"] = fee_rates_sorted[0]
        result["fee_p25"] = fee_rates_sorted[n // 4]
        result["fee_median"] = statistics.median(fee_rates_sorted)
        result["fee_p75"] = fee_rates_sorted[3 * n // 4]
        result["fee_max"] = fee_rates_sorted[-1]

    return result


def print_next_block(data: dict) -> None:
    """Print next block analysis to terminal."""
    print(f"{'NEXT BLOCK PREDICTION':=^60}")
    print(f"{'Height:':<25} {data['height']:,}")
    print(f"{'Transactions:':<25} {data['tx_count']:,}")
    print(
        f"{'Weight:':<25} {data['total_weight']:,} / {MAX_BLOCK_WEIGHT:,} "
        f"({data['weight_pct']:.1f}%)"
    )
    print()
    print(f"{'MINER REVENUE':=^60}")
    print(f"{'Subsidy:':<25} {format_btc(data['subsidy_sats'] / 1e8)}")
    print(f"{'Total fees:':<25} {format_btc(data['total_fee_sats'] / 1e8)}")
    print(f"{'Total revenue:':<25} {format_btc(data['total_revenue_sats'] / 1e8)}")

    if "fee_min" in data:
        print()
        print(f"{'FEE DISTRIBUTION':=^60}")
        print(f"{'Min:':<25} {data['fee_min']:.1f} sat/vB")
        print(f"{'25th percentile:':<25} {data['fee_p25']:.1f} sat/vB")
        print(f"{'Median:':<25} {data['fee_median']:.1f} sat/vB")
        print(f"{'75th percentile:':<25} {data['fee_p75']:.1f} sat/vB")
        print(f"{'Max:':<25} {data['fee_max']:.1f} sat/vB")

    if data["top_5"]:
        print()
        print(f"{'TOP 5 HIGHEST-FEE TXS':=^60}")
        for i, (txid, rate, fee) in enumerate(data["top_5"]):
            print(f"  [{i}] {txid[:16]}... → {rate:.1f} sat/vB ({format_sats(fee)})")


def main() -> None:
    try:
        rpc = BitcoinRPC()
        data = analyze_next_block(rpc)
        print_next_block(data)
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
