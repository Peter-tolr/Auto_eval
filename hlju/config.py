# -*- coding: utf-8 -*-
"""配置读取。"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_json(name: str, default=None):
    path = os.path.join(HERE, name)
    if not os.path.exists(path):
        return default if default is not None else {}
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_accounts() -> dict:
    return load_json("accounts.json", {})


def load_settings() -> dict:
    s = load_json("settings.json", {})
    s.setdefault("profile_dir", ".profiles")
    s.setdefault("min_avg", 0.9)
    s.setdefault("submit_wait", 8)
    s.setdefault("delay_between_forms", 3)
    return s
