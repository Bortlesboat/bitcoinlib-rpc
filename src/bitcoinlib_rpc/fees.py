"""Fee estimation and tracking with CSV logging."""

from __future__ import annotations

import csv
import sys
import time
from datetime import datetime
from pathlib import Path

from bitcoinlib_rpc.rpc import BitcoinRPC
from bitcoinlib_rpc.types import FeeEstimate
from bitcoinlib_rpc.utils import fee_recommendation

TARGETS = [1, 3, 6, 25, 144]


def get_fee_estimates(rpc: BitcoinRPC) -> list[FeeEstimate]:
    """Get fee estimates for standard confirmation targets."""
    estimates = []
    for target in TARGETS:
        result = rpc.estimatesmartfee(target)
        estimates.append(FeeEstimate.from_rpc(target, result))
    return estimates


def print_fees(estimates: list[FeeEstimate]) -> None:
    """Print fee estimates to terminal."""
    print(f"{'FEE ESTIMATES':=^60}")
    print(f"{'Target':<20} {'sat/vB':>10} {'BTC/kvB':>15}")
    print("-" * 60)

    labels = {1: "Next block", 3: "~30 min", 6: "~1 hour", 25: "~4 hours", 144: "~1 day"}

    for est in estimates:
        label = labels.get(est.conf_target, f"{est.conf_target} blocks")
        if est.errors:
            print(f"{label:<20} {'n/a':>10} {'(insufficient data)':>15}")
        else:
            print(f"{label:<20} {est.fee_rate_sat_vb:>10.1f} {est.fee_rate_btc_kvb:>15.8f}")

    # Recommendation
    rates = {e.conf_target: e.fee_rate_sat_vb for e in estimates if not e.errors}
    if rates:
        print()
        print(fee_recommendation(rates))


def log_to_csv(estimates: list[FeeEstimate], path: Path) -> None:
    """Append fee estimates to CSV file."""
    file_exists = path.exists()

    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(
                ["timestamp"]
                + [f"target_{t}" for t in TARGETS]
                + ["mempool_size"]
            )

        row = [datetime.now().isoformat()]
        for est in estimates:
            row.append(f"{est.fee_rate_sat_vb:.1f}" if not est.errors else "")
        row.append("")  # mempool_size placeholder
        writer.writerow(row)


def main() -> None:
    once = "--once" in sys.argv
    csv_path = None

    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--csv" and i < len(sys.argv) - 1:
            csv_path = Path(sys.argv[i + 1])

    try:
        rpc = BitcoinRPC()

        if once:
            estimates = get_fee_estimates(rpc)
            print_fees(estimates)
            if csv_path:
                log_to_csv(estimates, csv_path)
        else:
            print("Fee tracker running (Ctrl+C to stop)...")
            print()
            while True:
                estimates = get_fee_estimates(rpc)
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}]")
                print_fees(estimates)
                if csv_path:
                    log_to_csv(estimates, csv_path)
                time.sleep(60)

    except KeyboardInterrupt:
        print("\nStopped.")
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
