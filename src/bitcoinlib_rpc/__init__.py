"""bitcoinlib-rpc: Typed Python wrapper for Bitcoin Core RPC."""

from bitcoinlib_rpc.rpc import BitcoinRPC
from bitcoinlib_rpc.types import (
    BlockAnalysis,
    FeeEstimate,
    MempoolSummary,
    NodeStatus,
    TransactionAnalysis,
)

__version__ = "0.1.0"
__all__ = [
    "BitcoinRPC",
    "BlockAnalysis",
    "FeeEstimate",
    "MempoolSummary",
    "NodeStatus",
    "TransactionAnalysis",
]
