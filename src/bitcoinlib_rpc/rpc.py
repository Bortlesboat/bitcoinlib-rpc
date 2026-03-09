"""Bitcoin Core JSON-RPC client with cookie authentication."""

import json
import platform
from pathlib import Path
from typing import Any

import requests


class RPCError(Exception):
    """Bitcoin RPC error."""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"RPC error {code}: {message}")


class BitcoinRPC:
    """Typed Bitcoin Core JSON-RPC client.

    Supports cookie authentication (default) or user/password.
    Auto-detects the cookie file location based on OS and network.

    Usage:
        rpc = BitcoinRPC()  # auto-detect cookie
        info = rpc.getblockchaininfo()
        print(info["blocks"])
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8332,
        user: str | None = None,
        password: str | None = None,
        cookie_path: str | None = None,
        datadir: str | None = None,
        network: str = "mainnet",
        timeout: int = 120,
    ):
        self.url = f"http://{host}:{port}"
        self.timeout = timeout
        self._id = 0
        self._session = requests.Session()

        if user and password:
            self._session.auth = (user, password)
        else:
            cookie = self._find_cookie(cookie_path, datadir, network)
            if cookie:
                user, password = cookie.split(":")
                self._session.auth = (user, password)
            else:
                raise ConnectionError(
                    "No RPC credentials found. Provide user/password or ensure "
                    "Bitcoin Core is running with cookie authentication enabled."
                )

    def _find_cookie(
        self,
        cookie_path: str | None,
        datadir: str | None,
        network: str,
    ) -> str | None:
        """Find and read the .cookie file for authentication."""
        if cookie_path:
            p = Path(cookie_path)
            if p.exists():
                return p.read_text().strip()
            return None

        # Build candidate paths
        candidates: list[Path] = []

        if datadir:
            base = Path(datadir)
            if network == "testnet":
                candidates.append(base / "testnet3" / ".cookie")
            elif network == "signet":
                candidates.append(base / "signet" / ".cookie")
            elif network == "regtest":
                candidates.append(base / "regtest" / ".cookie")
            candidates.append(base / ".cookie")

        # OS-specific defaults
        system = platform.system()
        if system == "Windows":
            appdata = Path.home() / "AppData" / "Roaming" / "Bitcoin"
            candidates.append(appdata / ".cookie")
            # Common Windows datadir locations
            for drive in ["E:", "D:", "C:"]:
                candidates.append(Path(drive) / ".cookie")
        elif system == "Darwin":
            candidates.append(
                Path.home() / "Library" / "Application Support" / "Bitcoin" / ".cookie"
            )
        else:
            candidates.append(Path.home() / ".bitcoin" / ".cookie")

        for path in candidates:
            if path.exists():
                return path.read_text().strip()
        return None

    def call(self, method: str, *params: Any) -> Any:
        """Make a raw JSON-RPC call."""
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": method,
            "params": list(params),
        }
        try:
            resp = self._session.post(
                self.url,
                json=payload,
                timeout=self.timeout,
            )
        except requests.ConnectionError:
            raise ConnectionError(
                f"Cannot connect to Bitcoin node at {self.url}. "
                "Is bitcoind/bitcoin-qt running with server=1?"
            )

        if resp.status_code == 401:
            raise ConnectionError("RPC authentication failed. Check credentials.")

        data = resp.json()
        if data.get("error"):
            raise RPCError(data["error"]["code"], data["error"]["message"])
        return data["result"]

    # --- Blockchain ---

    def getblockchaininfo(self) -> dict:
        return self.call("getblockchaininfo")

    def getblockcount(self) -> int:
        return self.call("getblockcount")

    def getblockhash(self, height: int) -> str:
        return self.call("getblockhash", height)

    def getblock(self, blockhash: str, verbosity: int = 2) -> dict:
        return self.call("getblock", blockhash, verbosity)

    def getblockstats(self, hash_or_height: int | str) -> dict:
        return self.call("getblockstats", hash_or_height)

    def getchaintxstats(self, nblocks: int | None = None) -> dict:
        if nblocks is not None:
            return self.call("getchaintxstats", nblocks)
        return self.call("getchaintxstats")

    def getblockheader(self, blockhash: str, verbose: bool = True) -> dict | str:
        return self.call("getblockheader", blockhash, verbose)

    def getchaintips(self) -> list:
        return self.call("getchaintips")

    # --- Mempool ---

    def getmempoolinfo(self) -> dict:
        return self.call("getmempoolinfo")

    def getrawmempool(self, verbose: bool = False) -> dict | list:
        return self.call("getrawmempool", verbose)

    def getmempoolentry(self, txid: str) -> dict:
        return self.call("getmempoolentry", txid)

    def getmempoolancestors(self, txid: str, verbose: bool = False) -> list | dict:
        return self.call("getmempoolancestors", txid, verbose)

    # --- Transactions ---

    def getrawtransaction(self, txid: str, verbose: int = 2) -> dict | str:
        return self.call("getrawtransaction", txid, verbose)

    def decoderawtransaction(self, hexstring: str) -> dict:
        return self.call("decoderawtransaction", hexstring)

    def decodescript(self, hexstring: str) -> dict:
        return self.call("decodescript", hexstring)

    def sendrawtransaction(self, hexstring: str, maxfeerate: float | None = None) -> str:
        if maxfeerate is not None:
            return self.call("sendrawtransaction", hexstring, maxfeerate)
        return self.call("sendrawtransaction", hexstring)

    # --- Mining ---

    def getmininginfo(self) -> dict:
        return self.call("getmininginfo")

    def getblocktemplate(self, template_request: dict | None = None) -> dict:
        if template_request is None:
            template_request = {"rules": ["segwit"]}
        return self.call("getblocktemplate", template_request)

    # --- Fee estimation ---

    def estimatesmartfee(self, conf_target: int, mode: str = "ECONOMICAL") -> dict:
        return self.call("estimatesmartfee", conf_target, mode)

    # --- Network ---

    def getnetworkinfo(self) -> dict:
        return self.call("getnetworkinfo")

    def getpeerinfo(self) -> list:
        return self.call("getpeerinfo")

    def getconnectioncount(self) -> int:
        return self.call("getconnectioncount")

    # --- UTXO ---

    def gettxoutsetinfo(self) -> dict:
        return self.call("gettxoutsetinfo")

    def gettxout(self, txid: str, n: int, include_mempool: bool = True) -> dict | None:
        return self.call("gettxout", txid, n, include_mempool)

    def scantxoutset(self, action: str, scanobjects: list) -> dict:
        return self.call("scantxoutset", action, scanobjects)

    # --- Validation ---

    def validateaddress(self, address: str) -> dict:
        return self.call("validateaddress", address)

    # --- Help ---

    def help(self, command: str = "") -> str:
        if command:
            return self.call("help", command)
        return self.call("help")

    # --- Wallet (optional, may not be loaded) ---

    def getwalletinfo(self) -> dict:
        return self.call("getwalletinfo")
