from __future__ import annotations

import argparse
import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from .manager import (
    preview,
    register_from_toml,
    unregister_from_toml,
    load_config,
)


console = Console()


def _default_toml() -> str:
    # Prefer package co-located default, then workspace config, then CWD
    candidates = [
        # packaged default next to this __main__.py
        Path(__file__).resolve().parent / "owithu.toml",
        # repo root (src/.. -> project root)
        Path(__file__).resolve().parents[2] / "config" / "owithu.toml",
        Path.cwd() / "config" / "owithu.toml",
        Path.cwd() / "owithu.toml",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    # fallback relative path
    return str(Path(__file__).resolve().parent / "owithu.toml")


def main():
    parser = argparse.ArgumentParser(prog="owithu", description="Manage 'Open with' context menu entries via TOML")
    # allow interactive mode when no subcommand specified
    sub = parser.add_subparsers(dest="cmd", required=False)

    def add_common(p):
        p.add_argument("--config", "-c", default=_default_toml(), help="Path to owithu.toml")
        p.add_argument("--hive", choices=["HKCU", "HKCR", "HKLM"], default=None, help="Registry hive to write (omit to follow config)")
        p.add_argument("--interactive", "-i", action="store_true", help="Run with interactive prompts")
        p.add_argument("--yes", "-y", action="store_true", help="Assume yes for confirmations")

    p_reg = sub.add_parser("register", help="Register all entries from TOML")
    add_common(p_reg)
    p_reg.add_argument("--key", help="Only register the specific key (e.g., VSCode)")

    p_unreg = sub.add_parser("unregister", help="Remove entries from TOML")
    add_common(p_unreg)
    p_unreg.add_argument("--key", help="Only remove the specific key (e.g., VSCode)")

    p_show = sub.add_parser("preview", help="Preview entries from TOML")
    p_show.add_argument("--config", "-c", default=_default_toml(), help="Path to owithu.toml")

    args = parser.parse_args()

    # interactive main menu when no subcommand
    if args.cmd is None:
        console.print(Panel.fit("owithu 交互模式\n使用 TOML 批量管理右键菜单 'Open with …'", title="owithu", border_style="cyan"))
        cfg_guess = _default_toml()
        cfg = Prompt.ask("配置文件路径", default=cfg_guess)
        if not Path(cfg).exists():
            console.print(f"[red]找不到配置文件[/]: {cfg}")
            cfg2 = Prompt.ask("请再次输入配置文件路径 (或直接回车退出)", default="")
            if not cfg2:
                return
            cfg = cfg2
            if not Path(cfg).exists():
                console.print(f"[red]仍然找不到配置文件[/]: {cfg}")
                return

        action = Prompt.ask("选择操作", choices=["preview", "register", "unregister", "exit"], default="preview")
        if action == "exit":
            return
        hive = Prompt.ask("选择写入的注册表 Hive (留空则按配置决定)", choices=["HKCU", "HKCR", "HKLM", ""], default="") or None

        if action == "preview":
            _, _, entries = load_config(cfg)
            preview(entries)
            return

        if action == "register":
            _, _, entries = load_config(cfg)
            preview(entries)
            keys = [e.key for e in entries]
            console.print("可用键: " + ", ".join(keys))
            register_all = Confirm.ask("要注册所有条目吗?", default=True)
            if register_all:
                if not Confirm.ask(f"确认注册以上条目到 [bold]{hive}[/] ?", default=True):
                    console.print("已取消。")
                    return
                register_from_toml(cfg, hive=hive)
            else:
                sel = Prompt.ask("输入要注册的 key（逗号分隔）", default="")
                selected = [s.strip() for s in sel.split(",") if s.strip()]
                if not selected:
                    console.print("未选择任何条目，已取消。")
                    return
                if not Confirm.ask(f"确认注册 {', '.join(selected)} 到 [bold]{hive}[/] ?", default=True):
                    console.print("已取消。")
                    return
                for k in selected:
                    register_from_toml(cfg, hive=hive, only_key=k)
            console.print("[green]Done.[/]")
            return

        if action == "unregister":
            _, _, entries = load_config(cfg)
            keys = [e.key for e in entries]
            console.print("可用键: " + ", ".join(keys))
            remove_all = Confirm.ask("要移除所有条目吗?", default=False)
            if remove_all:
                if not Confirm.ask(f"确认从 [bold]{hive}[/] 移除全部?", default=False):
                    console.print("已取消。")
                    return
                unregister_from_toml(cfg, hive=hive, only_key=None)
                console.print("[yellow]已移除全部。[/]")
                return
            sel = Prompt.ask("输入要移除的 key（逗号分隔）", default="")
            selected = [s.strip() for s in sel.split(",") if s.strip()]
            if not selected:
                console.print("未选择任何条目，已取消。")
                return
            if not Confirm.ask(f"确认从 [bold]{hive}[/] 移除: {', '.join(selected)} ?", default=False):
                console.print("已取消。")
                return
            for k in selected:
                unregister_from_toml(cfg, hive=hive, only_key=k)
            console.print("[yellow]Done.[/]")
            return

    toml = args.config

    if args.cmd == "preview":
        _, _, entries = load_config(toml)
        preview(entries)
        return

    if args.cmd == "register":
        if getattr(args, "interactive", False):
            _, _, entries = load_config(toml)
            preview(entries)
            args.hive = (Prompt.ask("选择写入的注册表 Hive (留空则按配置决定)", choices=["HKCU", "HKCR", "HKLM", ""], default="") or None) if getattr(args, "interactive", False) else args.hive
            if not Confirm.ask(f"确认注册到 [bold]{args.hive}[/] ?", default=True):
                console.print("已取消。")
                return
        elif not getattr(args, "yes", False):
            hive_show = args.hive or "由配置决定"
            if not Confirm.ask(f"将注册到 [bold]{hive_show}[/]，确认继续?", default=True):
                console.print("已取消。")
                return
        register_from_toml(toml, hive=args.hive, only_key=getattr(args, "key", None))
        console.print("Done.")
    elif args.cmd == "unregister":
        if getattr(args, "interactive", False):
            _, _, entries = load_config(toml)
            keys = [e.key for e in entries]
            console.print("可用键: " + ", ".join(keys))
            args.hive = (Prompt.ask("选择目标注册表 Hive (留空则按配置决定)", choices=["HKCU", "HKCR", "HKLM", ""], default="") or None)
            if args.key:
                if not Confirm.ask(f"确认从 [bold]{args.hive}[/] 移除 {args.key} ?", default=True):
                    console.print("已取消。")
                    return
                unregister_from_toml(toml, hive=args.hive, only_key=args.key)
            else:
                remove_all = Confirm.ask("要移除所有条目吗?", default=False)
                if remove_all:
                    if not Confirm.ask(f"确认从 [bold]{args.hive}[/] 移除全部?", default=False):
                        console.print("已取消。")
                        return
                    unregister_from_toml(toml, hive=args.hive, only_key=None)
                else:
                    sel = Prompt.ask("输入要移除的 key（逗号分隔）", default="")
                    selected = [s.strip() for s in sel.split(",") if s.strip()]
                    for k in selected:
                        unregister_from_toml(toml, hive=args.hive, only_key=k)
        else:
            if not getattr(args, "yes", False) and not getattr(args, "key", None):
                if not Confirm.ask(f"将从 [bold]{args.hive}[/] 移除全部条目，确认继续?", default=False):
                    console.print("已取消。")
                    return
            unregister_from_toml(toml, hive=args.hive, only_key=getattr(args, "key", None))
        console.print("Done.")


if __name__ == "__main__":
    main()
