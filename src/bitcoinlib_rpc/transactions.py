"""Transaction decoding and analysis."""

from __future__ import annotations

import sys

from bitcoinlib_rpc.rpc import BitcoinRPC
from bitcoinlib_rpc.types import TransactionAnalysis, TransactionInput, TransactionOutput
from bitcoinlib_rpc.utils import (
    btc_to_sats,
    calc_fee_rate,
    detect_inscription,
    detect_script_type,
    extract_address,
    format_btc,
    format_sats,
)


def analyze_transaction(rpc: BitcoinRPC, txid: str) -> TransactionAnalysis:
    """Decode and analyze a transaction."""
    tx = rpc.getrawtransaction(txid, verbose=2)

    inputs: list[TransactionInput] = []
    total_input_sats = 0
    has_input_values = True

    for vin in tx.get("vin", []):
        if "coinbase" in vin:
            inputs.append(TransactionInput(
                txid="coinbase",
                vout=0,
                script_type="coinbase",
            ))
            has_input_values = False
            continue

        inp = TransactionInput(
            txid=vin["txid"],
            vout=vin["vout"],
        )

        # Try to resolve input value from previous tx
        try:
            prev_tx = rpc.getrawtransaction(vin["txid"], verbose=2)
            prev_out = prev_tx["vout"][vin["vout"]]
            inp.value_btc = prev_out["value"]
            inp.script_type = detect_script_type(prev_out["scriptPubKey"])
            inp.address = extract_address(prev_out["scriptPubKey"])
            total_input_sats += btc_to_sats(prev_out["value"])
        except Exception:
            has_input_values = False

        inputs.append(inp)

    outputs: list[TransactionOutput] = []
    total_output_sats = 0

    for vout in tx.get("vout", []):
        spk = vout["scriptPubKey"]
        stype = detect_script_type(spk)
        value_sats = btc_to_sats(vout["value"])
        total_output_sats += value_sats

        outputs.append(TransactionOutput(
            index=vout["n"],
            value_btc=vout["value"],
            value_sats=value_sats,
            script_type=stype,
            address=extract_address(spk),
            is_op_return=stype == "OP_RETURN",
        ))

    # Check for inscriptions in witness data
    has_insc = False
    insc_type = None
    for vin in tx.get("vin", []):
        witness = vin.get("txinwitness", [])
        if witness:
            found, ctype = detect_inscription(witness)
            if found:
                has_insc = True
                insc_type = ctype
                break

    # Determine SegWit and Taproot
    is_segwit = any(vin.get("txinwitness") for vin in tx.get("vin", []))
    is_taproot = any(
        o.script_type == "P2TR" for o in outputs
    ) or any(
        i.script_type == "P2TR" for i in inputs
    )

    # Fee calculation
    fee_sats = None
    fee_rate = None
    if has_input_values and total_input_sats > 0:
        fee_sats = total_input_sats - total_output_sats
        fee_rate = calc_fee_rate(fee_sats, tx.get("vsize", tx["size"]))

    return TransactionAnalysis(
        txid=tx["txid"],
        version=tx["version"],
        size=tx["size"],
        vsize=tx.get("vsize", tx["size"]),
        weight=tx.get("weight", tx["size"] * 4),
        locktime=tx.get("locktime", 0),
        inputs=inputs,
        outputs=outputs,
        fee_sats=fee_sats,
        fee_rate_sat_vb=fee_rate,
        is_segwit=is_segwit,
        is_taproot=is_taproot,
        has_inscription=has_insc,
        inscription_type=insc_type,
        block_hash=tx.get("blockhash"),
        confirmations=tx.get("confirmations"),
    )


def print_transaction(analysis: TransactionAnalysis) -> None:
    """Print transaction analysis to terminal."""
    print(f"{'TRANSACTION':=^60}")
    print(f"{'TXID:':<15} {analysis.txid}")
    print(f"{'Version:':<15} {analysis.version}")
    print(f"{'Size:':<15} {analysis.size} bytes")
    print(f"{'VSize:':<15} {analysis.vsize} vbytes")
    print(f"{'Weight:':<15} {analysis.weight} WU")
    print(f"{'Locktime:':<15} {analysis.locktime}")

    if analysis.confirmations is not None:
        print(f"{'Confirmations:':<15} {analysis.confirmations:,}")

    flags = []
    if analysis.is_segwit:
        flags.append("SegWit")
    if analysis.is_taproot:
        flags.append("Taproot")
    if analysis.has_inscription:
        flags.append(f"Inscription ({analysis.inscription_type or 'unknown'})")
    if flags:
        print(f"{'Flags:':<15} {', '.join(flags)}")

    if analysis.segwit_discount_pct > 0:
        print(f"{'SegWit saving:':<15} {analysis.segwit_discount_pct:.1f}%")

    print(f"\n{'INPUTS':=^60}")
    for i, inp in enumerate(analysis.inputs):
        val = format_btc(inp.value_btc) if inp.value_btc is not None else "?"
        addr = inp.address or ""
        print(f"  [{i}] {inp.script_type:<10} {val:>20}  {addr}")

    print(f"\n{'OUTPUTS':=^60}")
    for out in analysis.outputs:
        addr = out.address or ("OP_RETURN data" if out.is_op_return else "")
        print(f"  [{out.index}] {out.script_type:<10} {format_btc(out.value_btc):>20}  {addr}")

    if analysis.fee_sats is not None:
        print(f"\n{'FEE':=^60}")
        print(f"{'Fee:':<15} {format_sats(analysis.fee_sats)} ({format_btc(analysis.fee_sats / 1e8)})")
        if analysis.fee_rate_sat_vb is not None:
            print(f"{'Fee rate:':<15} {analysis.fee_rate_sat_vb:.1f} sat/vB")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: bitcoin-tx <txid>", file=sys.stderr)
        sys.exit(1)

    txid = sys.argv[1]
    try:
        rpc = BitcoinRPC()
        analysis = analyze_transaction(rpc, txid)
        print_transaction(analysis)
    except ConnectionError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
