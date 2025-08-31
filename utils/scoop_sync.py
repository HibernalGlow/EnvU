from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Python >=3.11 guaranteed by pyproject
import tomllib

from typing import Iterable, List


def run(cmd: List[str], cwd: str | None = None, check: bool = True, dry_run: bool = False) -> subprocess.CompletedProcess:
    if dry_run:
        print("DRYRUN:", " ".join(cmd))
        return subprocess.CompletedProcess(cmd, 0, b"", b"")
    print("> ", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd, check=check)


def powershell_args(script: str) -> List[str]:
    return [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]


@dataclass
class Options:
    remove_all_before_add: bool = True
    reset_core_repo: bool = True
    run_update: bool = True
    set_env: bool = False
    try_fix_ownership: bool = True
    dry_run: bool = False


@dataclass
class Config:
    root: str = "D:/scoop"
    repo: str | None = None
    buckets: list[tuple[str, str]] = None  # list of (name, url)
    options: Options = Options()


def load_config(path: Path) -> Config:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    scoop = data.get("scoop", {})
    opts = data.get("options", {})
    buckets = [(b["name"], b.get("url", "")) for b in data.get("bucket", [])]
    return Config(
        root=scoop.get("root", "D:/scoop"),
        repo=scoop.get("repo"),
        buckets=buckets,
        options=Options(
            remove_all_before_add=opts.get("remove_all_before_add", True),
            reset_core_repo=opts.get("reset_core_repo", True),
            run_update=opts.get("run_update", True),
            set_env=opts.get("set_env", False),
            try_fix_ownership=opts.get("try_fix_ownership", True),
            dry_run=opts.get("dry_run", False),
        ),
    )


def ensure_git_safe_dirs(root: str, dry_run: bool) -> None:
    # Add core and each bucket path as safe.directory to avoid Git dubious ownership
    candidates: List[str] = []
    candidates.append(os.path.join(root, "apps", "scoop", "current"))
    buckets_dir = os.path.join(root, "buckets")
    if os.path.isdir(buckets_dir):
        for name in os.listdir(buckets_dir):
            p = os.path.join(buckets_dir, name)
            if os.path.isdir(os.path.join(p, ".git")):
                candidates.append(p)
    for p in candidates:
        p_slash = p.replace("\\", "/")
        run(["git", "config", "--global", "--add", "safe.directory", p_slash], dry_run=dry_run)


def remove_all_buckets(dry_run: bool) -> None:
    # Get installed buckets via 'scoop bucket list' and remove them
    ps = (
        "$ErrorActionPreference='SilentlyContinue';"
        "$names = scoop bucket list | Select-String -NotMatch '^Name|^----|^$' | ForEach-Object { ($_ -split ' +')[0] } | Sort-Object -Unique;"
        "foreach ($n in $names) { scoop bucket rm $n }"
    )
    run(powershell_args(ps), dry_run=dry_run)


def reset_core_repo(root: str, dry_run: bool) -> None:
    core = os.path.join(root, "apps", "scoop", "current")
    if os.path.isdir(os.path.join(core, ".git")):
        run(["git", "-C", core, "reset", "--hard", "HEAD"], dry_run=dry_run)
        run(["git", "-C", core, "clean", "-fd"], dry_run=dry_run)


def add_buckets(buckets: Iterable[tuple[str, str]], dry_run: bool) -> None:
    for name, url in buckets:
        if url:
            run(["scoop", "bucket", "add", name, url], dry_run=dry_run)
        else:
            run(["scoop", "bucket", "add", name], dry_run=dry_run)


def set_repo_mirror(repo: str | None, dry_run: bool) -> None:
    if repo:
        run(["scoop", "config", "SCOOP_REPO", repo], dry_run=dry_run)


def set_env_scoop(root: str, dry_run: bool) -> None:
    # Set user env var SCOOP
    ps = (
        f"[Environment]::SetEnvironmentVariable('SCOOP','{root}','User')"
    )
    run(powershell_args(ps), dry_run=dry_run)


def run_update(dry_run: bool) -> None:
    run(["scoop", "update"], dry_run=dry_run, check=False)


def main(argv: List[str]) -> int:
    cfg_path = Path(__file__).with_name("..").resolve().parent / "config" / "scoop.toml"
    # Prefer fixed relative path from repo root if running from anywhere
    repo_root = Path(__file__).resolve().parents[1]
    cfg_path = repo_root / "config" / "scoop.toml"
    if not cfg_path.exists():
        print(f"Config not found: {cfg_path}")
        return 2

    cfg = load_config(cfg_path)

    if cfg.options.try_fix_ownership:
        ensure_git_safe_dirs(cfg.root, cfg.options.dry_run)

    if cfg.options.remove_all_before_add:
        remove_all_buckets(cfg.options.dry_run)

    if cfg.options.reset_core_repo:
        reset_core_repo(cfg.root, cfg.options.dry_run)

    if cfg.options.set_env:
        set_env_scoop(cfg.root, cfg.options.dry_run)

    set_repo_mirror(cfg.repo, cfg.options.dry_run)

    add_buckets(cfg.buckets, cfg.options.dry_run)

    if cfg.options.run_update:
        run_update(cfg.options.dry_run)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
