"""Pydantic models for typed Bitcoin RPC responses."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NodeStatus(BaseModel):
    """Summary of node state."""

    chain: str
    blocks: int
    headers: int
    verification_progress: float
    size_on_disk: int
    pruned: bool
    connections: int
    version: int
    subversion: str
    network_name: str = ""

    @property
    def synced(self) -> bool:
        return self.verification_progress > 0.9999

    @property
    def size_on_disk_gb(self) -> float:
        return self.size_on_disk / 1e9


class FeeEstimate(BaseModel):
    """Fee estimate for a confirmation target."""

    conf_target: int
    fee_rate_btc_kvb: float = Field(description="BTC per kilovirtual byte")
    fee_rate_sat_vb: float = Field(description="Satoshis per virtual byte")
    errors: list[str] = Field(default_factory=list)

    @classmethod
    def from_rpc(cls, conf_target: int, rpc_result: dict) -> FeeEstimate:
        fee_rate = rpc_result.get("feerate", 0.0)
        return cls(
            conf_target=conf_target,
            fee_rate_btc_kvb=fee_rate,
            fee_rate_sat_vb=fee_rate * 100_000,
            errors=rpc_result.get("errors", []),
        )


class FeeBucket(BaseModel):
    """A bucket of transactions grouped by fee rate."""

    min_rate: float
    max_rate: float
    label: str
    count: int = 0
    total_vsize: int = 0

    @property
    def total_vsize_mb(self) -> float:
        return self.total_vsize / 1_000_000


class MempoolSummary(BaseModel):
    """Analyzed mempool snapshot."""

    size: int = Field(description="Number of unconfirmed transactions")
    total_bytes: int = Field(description="Total mempool size in bytes")
    total_fee_btc: float = Field(description="Total fees in BTC")
    min_relay_fee: float
    buckets: list[FeeBucket] = Field(default_factory=list)
    next_block_min_fee: float = Field(
        0.0, description="Minimum fee rate to enter next block (sat/vB)"
    )
    congestion: str = Field("unknown", description="low/moderate/high/extreme")
    timestamp: datetime = Field(default_factory=datetime.now)


class TransactionInput(BaseModel):
    """Parsed transaction input."""

    txid: str
    vout: int
    script_type: str = "unknown"
    value_btc: Optional[float] = None
    address: Optional[str] = None


class TransactionOutput(BaseModel):
    """Parsed transaction output."""

    index: int
    value_btc: float
    value_sats: int
    script_type: str
    address: Optional[str] = None
    is_op_return: bool = False


class TransactionAnalysis(BaseModel):
    """Full transaction analysis."""

    txid: str
    version: int
    size: int
    vsize: int
    weight: int
    locktime: int
    inputs: list[TransactionInput] = Field(default_factory=list)
    outputs: list[TransactionOutput] = Field(default_factory=list)
    fee_sats: Optional[int] = None
    fee_rate_sat_vb: Optional[float] = None
    is_segwit: bool = False
    is_taproot: bool = False
    has_inscription: bool = False
    inscription_type: Optional[str] = None
    block_hash: Optional[str] = None
    confirmations: Optional[int] = None

    @property
    def total_output_btc(self) -> float:
        return sum(o.value_btc for o in self.outputs)

    @property
    def segwit_discount_pct(self) -> float:
        if self.size == 0:
            return 0.0
        legacy_weight = self.size * 4
        return (1 - self.weight / legacy_weight) * 100


class BlockAnalysis(BaseModel):
    """Analyzed block."""

    height: int
    hash: str
    timestamp: datetime
    version: int
    size: int
    weight: int
    tx_count: int
    pool_name: str = "Unknown"
    subsidy_btc: float = 3.125
    total_fee_btc: float = 0.0
    total_revenue_btc: float = 0.0
    weight_utilization_pct: float = 0.0
    segwit_tx_count: int = 0
    taproot_tx_count: int = 0
    segwit_pct: float = 0.0
    taproot_pct: float = 0.0
    fee_rate_min: float = 0.0
    fee_rate_median: float = 0.0
    fee_rate_max: float = 0.0
    top_fee_txids: list[tuple[str, float]] = Field(default_factory=list)
