#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple


def is_admin() -> bool:
    try:
        if os.name == 'nt':
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        else:
            return os.geteuid() == 0
    except Exception:
        return False


def create_symlink(source: Path, target: Path) -> Tuple[bool, str | None]:
    try:
        if os.name == 'nt':
            if source.is_dir():
                cmd = f'mklink /D "{target}" "{source}"'
            else:
                cmd = f'mklink "{target}" "{source}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='gbk')
            if result.returncode == 0:
                return True, None
            return False, result.stderr
        else:
            os.symlink(source, target)
            return True, None
    except Exception as e:
        return False, str(e)


def delete_symlink(path: Path) -> Tuple[bool, str | None]:
    try:
        path.unlink()
        return True, None
    except Exception as e1:
        # Windows 兜底
        try:
            if os.name == 'nt':
                # 尝试判断是否目录软链
                is_dir_link = False
                try:
                    if path.exists() and path.is_dir():
                        is_dir_link = True
                    else:
                        tgt = path.readlink()
                        is_dir_link = Path(tgt).is_dir()
                except Exception:
                    is_dir_link = True
                if is_dir_link:
                    subprocess.run(f'rmdir "{path}"', shell=True, check=True)
                else:
                    subprocess.run(f'del "{path}"', shell=True, check=True)
                return True, None
            return False, str(e1)
        except Exception as e2:
            return False, f"{e1}; {e2}"


def move_dir_with_skip(source: Path, target: Path, on_skip=None) -> Tuple[bool, int, int]:
    """移动目录，跳过失败的文件。
    返回 (success, moved_count, total_files)
    """
    failed_files = []
    total_files = 0
    try:
        shutil.move(str(source), str(target))
        return True, 0, 0
    except Exception:
        pass

    try:
        target.mkdir(parents=True, exist_ok=True)
        for root, dirs, files in os.walk(source):
            total_files += len(files)

        moved_count = 0
        for root, dirs, files in os.walk(source):
            rel = Path(root).relative_to(source)
            dst_dir = target / rel
            try:
                dst_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                continue
            for fn in files:
                src_f = Path(root) / fn
                dst_f = dst_dir / fn
                try:
                    shutil.move(str(src_f), str(dst_f))
                    moved_count += 1
                except Exception as e:
                    failed_files.append((str(src_f), str(e)))
                    if on_skip:
                        on_skip(src_f, e)

        # 清理空目录
        try:
            if source.exists():
                for root, dirs, files in os.walk(source, topdown=False):
                    for d in dirs:
                        p = Path(root) / d
                        try:
                            if not any(p.iterdir()):
                                p.rmdir()
                        except Exception:
                            pass
                if not any(source.iterdir()):
                    source.rmdir()
        except Exception:
            pass

        success_rate = (moved_count / total_files) * 100 if total_files > 0 else 100.0
        return success_rate >= 90.0, moved_count, total_files
    except Exception:
        return False, 0, 0
