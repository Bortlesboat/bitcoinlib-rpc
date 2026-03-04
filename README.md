# bitcoinlib-rpc

Typed Python wrapper for Bitcoin Core RPC with analysis tools.

Query your Bitcoin node with typed responses, analyze mempool fee markets, decode transactions, and inspect blocks — all from Python or the command line.

## Install

```bash
pip install bitcoinlib-rpc
```

Or from source:

```bash
git clone https://github.com/Bortlesboat/bitcoinlib-rpc.git
cd bitcoinlib-rpc
pip install -e .
```

## Requirements

- Python 3.10+
- A running Bitcoin Core or Bitcoin Knots node with `server=1` in bitcoin.conf
- `txindex=1` recommended (required for transaction lookups by txid)

## Quick Start

### Python API

```python
from bitcoinlib_rpc import BitcoinRPC

rpc = BitcoinRPC()  # auto-detects cookie authentication

# Node status
info = rpc.getblockchaininfo()
print(f"Block height: {info['blocks']:,}")

# Fee estimates
fee = rpc.estimatesmartfee(6)
print(f"6-block fee: {fee['feerate'] * 100_000:.1f} sat/vB")

# Decode a transaction
tx = rpc.getrawtransaction("a1075db5...", verbose=2)
```

### Typed Analysis Objects

```python
from bitcoinlib_rpc import BitcoinRPC
from bitcoinlib_rpc.mempool import analyze_mempool
from bitcoinlib_rpc.transactions import analyze_transaction
from bitcoinlib_rpc.blocks import analyze_block

rpc = BitcoinRPC()

# Mempool snapshot with fee bucketing
mempool = analyze_mempool(rpc)
print(f"Congestion: {mempool.congestion}")
print(f"Next block min fee: {mempool.next_block_min_fee:.1f} sat/vB")

# Transaction analysis with inscription detection
tx = analyze_transaction(rpc, "a1075db5...")
print(f"Fee rate: {tx.fee_rate_sat_vb:.1f} sat/vB")
print(f"SegWit discount: {tx.segwit_discount_pct:.1f}%")

# Block analysis with pool identification
block = analyze_block(rpc, 939290)
print(f"Mined by: {block.pool_name}")
print(f"Taproot adoption: {block.taproot_pct:.1f}%")
```

### Command Line Tools

```bash
# Node status
bitcoin-status

# Mempool analysis
bitcoin-mempool

# Decode a transaction
bitcoin-tx a1075db55d416d3ca199f55b6084e2115b9345e16c5cf302fc80e9d5fbf5d48d

# Analyze a block
bitcoin-block 939290

# Fee estimates
bitcoin-fees --once

# Continuous fee tracking with CSV log
bitcoin-fees --csv fees.csv

# Next block prediction
bitcoin-nextblock
```

## Tools

| Command | What it does |
|---------|-------------|
| `bitcoin-status` | Node chain, sync, disk, peers |
| `bitcoin-mempool` | Fee buckets, congestion, next-block estimate |
| `bitcoin-tx <txid>` | Full tx decode + inscription detection |
| `bitcoin-block <height>` | Pool ID, SegWit/Taproot adoption, fee distribution |
| `bitcoin-fees` | Fee targets for 1/3/6/25/144 blocks |
| `bitcoin-nextblock` | Block template: weight, revenue, fee distribution |

## Authentication

The library auto-detects the `.cookie` file from standard Bitcoin Core locations:

- **Windows:** `%APPDATA%\Bitcoin\.cookie` or common datadirs (E:\, D:\)
- **macOS:** `~/Library/Application Support/Bitcoin/.cookie`
- **Linux:** `~/.bitcoin/.cookie`

Or provide credentials explicitly:

```python
rpc = BitcoinRPC(user="rpcuser", password="rpcpassword")
rpc = BitcoinRPC(cookie_path="/path/to/.cookie")
rpc = BitcoinRPC(datadir="/mnt/bitcoin")
```

## Related

- [Bitcoin Protocol Guide](https://bortlesboat.github.io/bitcoin-protocol-guide/) — the educational guide this library accompanies
- [Bitcoin Core RPC Reference](https://developer.bitcoin.org/reference/rpc/)

## License

MIT
