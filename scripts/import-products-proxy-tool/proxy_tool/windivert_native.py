from __future__ import annotations

import ctypes
import os
from pathlib import Path

from .config import VENDOR_WINDIVERT
from .errors import PrivilegeError


WINDIVERT_LAYER_NETWORK = 0
WINDIVERT_LAYER_SOCKET = 3

WINDIVERT_FLAG_DROP = 0x0002
WINDIVERT_FLAG_RECV_ONLY = 0x0004

INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class WinDivertHandle:
    def __init__(
        self,
        filter_text: str,
        layer: int,
        priority: int,
        flags: int,
    ):
        self.filter_text = filter_text
        self.layer = layer
        self.priority = priority
        self.flags = flags

        dll_path = VENDOR_WINDIVERT / "WinDivert.dll"
        sys_path = VENDOR_WINDIVERT / "WinDivert64.sys"

        if not dll_path.exists() or not sys_path.exists():
            raise PrivilegeError(
                "WinDivert binaries are missing. Run bootstrap.ps1."
            )

        self._dll_dir_handle = None

        if hasattr(os, "add_dll_directory"):
            self._dll_dir_handle = os.add_dll_directory(
                str(VENDOR_WINDIVERT)
            )

        self.dll = ctypes.WinDLL(
            str(dll_path),
            use_last_error=True,
        )

        self.dll.WinDivertOpen.argtypes = [
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_short,
            ctypes.c_uint64,
        ]
        self.dll.WinDivertOpen.restype = ctypes.c_void_p

        self.dll.WinDivertClose.argtypes = [ctypes.c_void_p]
        self.dll.WinDivertClose.restype = ctypes.c_bool

        self.handle = None

    def open(self) -> None:
        handle = self.dll.WinDivertOpen(
            self.filter_text.encode("ascii"),
            self.layer,
            self.priority,
            self.flags,
        )

        if handle in {None, 0, INVALID_HANDLE_VALUE}:
            error = ctypes.get_last_error()

            if error in {5, 577, 1275}:
                raise PrivilegeError(
                    "WinDivert driver could not be opened. "
                    f"Windows error={error}. "
                    "Run as Administrator. If Windows Security, HVCI, "
                    "Secure Boot, or antivirus blocks the signed driver, "
                    "do not disable those protections automatically."
                )

            raise OSError(
                error,
                f"WinDivertOpen failed for layer={self.layer}",
            )

        self.handle = handle

    def close(self) -> None:
        if self.handle:
            self.dll.WinDivertClose(self.handle)
            self.handle = None

        if self._dll_dir_handle is not None:
            try:
                self._dll_dir_handle.close()
            except Exception:
                pass
            self._dll_dir_handle = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


class KillSwitch:
    def __init__(
        self,
        gate_pid: int,
        proxy_ips: list[str],
        proxy_port: int,
    ):
        if not proxy_ips:
            raise ValueError("At least one proxy IPv4 address is required.")

        # WinDivert's filter grammar has no negated parenthesised group,
        # so the allow-rule is expressed with De Morgan's law:
        # not (tcp and dst in proxy_ips and dport == P)
        #   == (tcp == 0 or (dst != A and dst != B ...) or dport != P)
        ip_not_allowed = " and ".join(
            f"ip.DstAddr != {ip}"
            for ip in proxy_ips
        )

        # All outbound IPv6 is blocked.
        # IPv4 is blocked unless it is TCP to the pinned upstream proxy.
        network_filter = (
            "outbound and !loopback and "
            "("
            "ipv6 or "
            "(ip and ("
            "tcp == 0 or "
            f"({ip_not_allowed}) or "
            f"tcp.DstPort != {int(proxy_port)}"
            "))"
            ")"
        )

        # Only the gate process is permitted to create non-loopback sockets.
        socket_filter = (
            "event == CONNECT and "
            "!loopback and "
            f"processId != {int(gate_pid)}"
        )

        self.socket_handle = WinDivertHandle(
            socket_filter,
            layer=WINDIVERT_LAYER_SOCKET,
            priority=30000,
            flags=WINDIVERT_FLAG_DROP | WINDIVERT_FLAG_RECV_ONLY,
        )

        self.network_handle = WinDivertHandle(
            network_filter,
            layer=WINDIVERT_LAYER_NETWORK,
            priority=30000,
            flags=WINDIVERT_FLAG_DROP,
        )

    def open(self) -> None:
        # Socket restriction first. The gate is already idle/listening.
        self.socket_handle.open()

        try:
            self.network_handle.open()
        except Exception:
            self.socket_handle.close()
            raise

    def close(self) -> None:
        # Remove packet-level enforcement last.
        self.socket_handle.close()
        self.network_handle.close()

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()