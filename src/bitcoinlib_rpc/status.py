"""Node status summary."""

from __future__ import annotations

import sys

from bitcoinlib_rpc.rpc import BitcoinRPC
from bitcoinlib_rpc.types import NodeStatus
from bitcoinlib_rpc.utils import format_size


def get_status(rpc: BitcoinRPC) -> NodeStatus:
    """Get node status as a typed object."""
    chain = rpc.getblockchaininfo()
    net = rpc.getnetworkinfo()
    peers = rpc.getconnectioncount()

    return NodeStatus(
        chain=chain["chain"],
        blocks=chain["blocks"],
        headers=chain["headers"],
        verification_progress=chain["verificationprogress"],
        size_on_disk=chain["size_on_disk"],
        pruned=chain["pruned"],
        connections=peers,
        version=net["version"],
        subversion=net["subversion"],
        network_name=net.get("subversion", ""),
    )


def print_status(status: NodeStatus) -> None:
    """Print node status to terminal."""
    sync = "SYNCED" if status.synced else f"{status.verification_progress:.2%}"
    print(f"{'Chain:':<20} {status.chain}")
    print(f"{'Block height:':<20} {status.blocks:,}")
    print(f"{'Headers:':<20} {status.headers:,}")
    print(f"{'Sync status:':<20} {sync}")
    print(f"{'Size on disk:':<20} {format_size(status.size_on_disk)}")
    print(f"{'Pruned:':<20} {'Yes' if status.pruned else 'No'}")
    print(f"{'Connections:':<20} {status.connections}")
    print(f"{'Node version:':<20} {status.subversion}")


def main() -> None:
    try:
        rpc = BitcoinRPC()
        status = get_status(rpc)
        print_status(status)
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
