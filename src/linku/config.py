#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConfigStore:
    """
    简单的 TOML 配置存储，默认保存在包目录同级：<package>/linku.toml
    仅支持本工具生成的数据结构：
    {
      config_version: int,
      links: [ { link, target, type, created_at } ]
    }
    """

    def __init__(self, file_path: Optional[Path] = None) -> None:
        if file_path is None:
            # 默认放在包目录
            pkg_dir = Path(__file__).resolve().parent
            file_path = pkg_dir / 'linku.toml'
        self.file_path: Path = file_path
        self.data: Dict[str, Any] = {"config_version": 1, "links": []}
        self.reload()

    # ---------- IO ----------
    def reload(self) -> None:
        if not self.file_path.exists():
            # 确保目录存在
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.data = {"config_version": 1, "links": []}
            return
        try:
            try:
                import tomllib  # py311+
            except ModuleNotFoundError:
                tomllib = None
            if tomllib:
                with self.file_path.open('rb') as f:
                    self.data = tomllib.load(f)
            else:
                # 极简兜底解析（仅适配本工具输出）
                self.data = {"config_version": 1, "links": []}
                current: Optional[Dict[str, Any]] = None
                for line in self.file_path.read_text(encoding='utf-8').splitlines():
                    s = line.strip()
                    if not s or s.startswith('#'):
                        continue
                    if s.startswith('config_version'):
                        try:
                            self.data['config_version'] = int(s.split('=')[1].strip())
                        except Exception:
                            pass
                    elif s == '[[links]]':
                        current = {}
                        self.data['links'].append(current)
                    elif '=' in s and current is not None:
                        k, v = s.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"')
                        v = v.replace('\\"', '"').replace('\\\\', '\\')
                        current[k] = v
            self.data.setdefault('config_version', 1)
            self.data.setdefault('links', [])
        except Exception:
            # 失败则回退默认
            self.data = {"config_version": 1, "links": []}

    def _escape(self, s: str) -> str:
        return s.replace('\\', '\\\\').replace('"', '\\"')

    def _dump(self) -> str:
        lines: List[str] = []
        lines.append('# linku 配置（自动生成）')
        lines.append(f"config_version = {int(self.data.get('config_version', 1))}")
        lines.append('')
        links = self.data.get('links', []) or []
        for item in links:
            lines.append('[[links]]')
            for key in ("link", "target", "type", "created_at"):
                if key in item and item[key] is not None:
                    lines.append(f'{key} = "{self._escape(str(item[key]))}"')
            lines.append('')
        return "\n".join(lines).rstrip() + "\n"

    def save(self) -> None:
        tmp = self.file_path.with_suffix('.toml.tmp')
        tmp.write_text(self._dump(), encoding='utf-8')
        tmp.replace(self.file_path)

    # ---------- 操作 ----------
    def record_link(self, link_path: Path, target_path: Path, link_type: str) -> None:
        link_key = str(link_path)
        target_val = str(target_path)
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        def norm(p: str) -> str:
            return p.lower() if os.name == 'nt' else p

        existing = None
        for item in self.data.get('links', []):
            if norm(item.get('link', '')) == norm(link_key):
                existing = item
                break
        if existing:
            existing['target'] = target_val
            existing['type'] = link_type
            existing['created_at'] = now_iso
        else:
            self.data.setdefault('links', []).append({
                'link': link_key,
                'target': target_val,
                'type': link_type,
                'created_at': now_iso,
            })
        self.save()

    def remove_link_record(self, link_path: Path) -> bool:
        def norm(p: str) -> str:
            return p.lower() if os.name == 'nt' else p
        key = norm(str(link_path))
        links = self.data.get('links', [])
        original_len = len(links)
        links = [item for item in links if norm(item.get('link', '')) != key]
        if len(links) != original_len:
            self.data['links'] = links
            self.save()
            return True
        return False

    def get_links(self) -> List[Dict[str, Any]]:
        return list(self.data.get('links', []) or [])
