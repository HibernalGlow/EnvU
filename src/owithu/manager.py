from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from typing import Iterable, Literal, Optional

import winreg
from rich.console import Console
from rich.table import Table

Scope = Literal["file", "directory", "background"]


console = Console()


@dataclass
class Entry:
    key: str
    label: str
    exe: str
    args: list[str]
    icon: Optional[str]
    scope: list[Scope]


def _norm_path(p: str) -> str:
    # Accept forward slashes in TOML, normalize to Windows style
    return os.path.normpath(p)


def _quote_arg(arg: str) -> str:
    # Ensure %1/%V are quoted to support spaces in paths
    if arg in {"%1", "%V"}:
        return f'"{arg}"'
    # If already quoted or contains no spaces, leave as-is or quote if spaces
    if (arg.startswith('"') and arg.endswith('"')) or (" " not in arg):
        return arg
    return f'"{arg}"'


def _build_command(exe: str, args: Iterable[str]) -> str:
    exe_q = exe
    if not exe_q.startswith('"'):
        exe_q = f'"{exe_q}"'
    joined = " ".join(_quote_arg(a) for a in args)
    return f"{exe_q} {joined}" if joined else exe_q


def _open_root(hive: str) -> winreg.HKEYType:
    hive = hive.upper()
    if hive == "HKCR":
        return winreg.HKEY_CLASSES_ROOT
    if hive == "HKCU":
        return winreg.HKEY_CURRENT_USER
    if hive == "HKLM":
        return winreg.HKEY_LOCAL_MACHINE
    raise ValueError(f"Unsupported hive: {hive}")


def _base_classes_path(hive: str) -> tuple[winreg.HKEYType, str]:
    if hive.upper() == "HKCU":
        # write to per-user classes to avoid admin
        return (winreg.HKEY_CURRENT_USER, r"Software\Classes")
    if hive.upper() == "HKCR":
        # writing HKCR may require admin
        return (winreg.HKEY_CLASSES_ROOT, "")
    if hive.upper() == "HKLM":
        return (winreg.HKEY_LOCAL_MACHINE, r"Software\Classes")
    raise ValueError(f"Unsupported hive: {hive}")


def _ensure_key(root: winreg.HKEYType, subkey: str):
    return winreg.CreateKeyEx(root, subkey, 0, access=winreg.KEY_ALL_ACCESS)


def _set_value(key_handle, name: Optional[str], value: str):
    winreg.SetValueEx(key_handle, name, 0, winreg.REG_SZ, value)


def _delete_tree(root: winreg.HKEYType, subkey: str):
    try:
        with winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS) as k:
            # Recursively delete
            while True:
                try:
                    child = winreg.EnumKey(k, 0)
                except OSError:
                    break
                _delete_tree(root, f"{subkey}\\{child}")
        winreg.DeleteKey(root, subkey)
    except FileNotFoundError:
        return


def _scoped_key_paths(entry_key: str, scope: Scope) -> list[str]:
    paths = []
    if scope == "file":
        paths.append(rf"*\\shell\\{entry_key}")
    elif scope == "directory":
        paths.append(rf"Directory\\shell\\{entry_key}")
    elif scope == "background":
        paths.append(rf"Directory\\Background\\shell\\{entry_key}")
    return paths


def load_config(toml_path: str) -> tuple[dict, list[Entry]]:
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)

    vars_map = data.get("vars", {}) or {}
    entries_data = data.get("entries", []) or []

    entries: list[Entry] = []
    for e in entries_data:
        key = e["key"]
        label = e.get("label", key)
        exe = e["exe"].format(**vars_map)
        icon = (e.get("icon") or e["exe"]).format(**vars_map)
        args = e.get("args", [])
        scope = e.get("scope", ["file"])  # default to file only
        # Normalize paths
        exe = _norm_path(exe)
        icon = _norm_path(icon)
        entries.append(Entry(key=key, label=label, exe=exe, args=args, icon=icon, scope=scope))

    return vars_map, entries


def register_entries(entries: list[Entry], hive: str = "HKCU"):
    root, base = _base_classes_path(hive)
    for e in entries:
        for sc in e.scope:
            for path in _scoped_key_paths(e.key, sc):
                full = f"{base}\\{path}" if base else path
                with _ensure_key(root, full) as h:
                    _set_value(h, None, e.label)
                    _set_value(h, "Icon", e.icon)
                # command subkey
                with _ensure_key(root, f"{full}\\command") as hc:
                    # Replace placeholder for scope: file -> %1; others -> %V
                    args = ["%V" if (a == "%1" and sc in {"directory", "background"}) else a for a in e.args]
                    cmd = _build_command(e.exe, args)
                    _set_value(hc, None, cmd)
                console.print(f"[green]Registered[/] {e.key} -> {full}")


def unregister_entries(entries: list[Entry], hive: str = "HKCU", only_key: Optional[str] = None):
    root, base = _base_classes_path(hive)
    for e in entries:
        if only_key and e.key != only_key:
            continue
        for sc in e.scope:
            for path in _scoped_key_paths(e.key, sc):
                full = f"{base}\\{path}" if base else path
                _delete_tree(root, full)
                console.print(f"[yellow]Removed[/] {e.key} <- {full}")


def preview(entries: list[Entry]):
    table = Table(title="owithu entries")
    table.add_column("Key")
    table.add_column("Label")
    table.add_column("Scopes")
    table.add_column("Exe")
    table.add_column("Args")
    for e in entries:
        table.add_row(e.key, e.label, ",".join(e.scope), e.exe, " ".join(e.args))
    console.print(table)


def register_from_toml(toml_path: str, hive: str = "HKCU"):
    _, entries = load_config(toml_path)
    register_entries(entries, hive=hive)


def unregister_from_toml(toml_path: str, hive: str = "HKCU", only_key: Optional[str] = None):
    _, entries = load_config(toml_path)
    unregister_entries(entries, hive=hive, only_key=only_key)
