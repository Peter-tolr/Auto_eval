# -*- coding: utf-8 -*-
"""浏览器启动与通用等待/截图工具。"""
from __future__ import annotations

import os
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT_DIR = os.path.join(HERE, "screenshots")
DUMP_DIR = os.path.join(HERE, "dumps")

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _edge_binary() -> str | None:
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def launch(profile: str, headless: bool = False, download_dir: str | None = None) -> webdriver.Edge:
    o = Options()
    exe = _edge_binary()
    if exe:
        o.binary_location = exe
    o.add_argument("--user-data-dir=" + profile)
    o.add_argument("--no-first-run")
    o.add_argument("--no-default-browser-check")
    o.add_argument("--disable-features=msEdgeFirstRunExperience,msEdgeSidebar")
    o.add_argument("--disable-background-networking")
    o.add_argument("--disable-sync")
    o.add_argument("--window-size=1440,1000")
    if headless:
        o.add_argument("--headless=new")
    o.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    o.add_experimental_option("useAutomationExtension", False)
    if download_dir:
        o.add_experimental_option("prefs", {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
        })
    o.page_load_strategy = "eager"
    d = webdriver.Edge(options=o)
    d.set_page_load_timeout(90)
    d.set_script_timeout(60)
    try:
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        })
    except Exception:
        pass
    return d


def body_text(d) -> str:
    try:
        return (d.find_element(By.TAG_NAME, "body").text or "").strip()
    except Exception:
        return ""


def screenshot(d, name: str) -> str:
    os.makedirs(SHOT_DIR, exist_ok=True)
    path = os.path.join(SHOT_DIR, name + ".png")
    try:
        d.save_screenshot(path)
    except Exception:
        pass
    return path


def dump_html(d, name: str) -> str:
    os.makedirs(DUMP_DIR, exist_ok=True)
    path = os.path.join(DUMP_DIR, name + ".html")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(d.page_source)
    except Exception:
        pass
    return path


def wait_until(fn, timeout: float = 60, interval: float = 1.0, desc: str = "") -> bool:
    end = time.time() + timeout
    while time.time() < end:
        try:
            if fn():
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def click_text(d, text: str, tags=("button", "a", "div", "span", "li")) -> bool:
    """按可见文本点击元素（精确匹配优先，其次包含匹配）。"""
    xp = " | ".join("self::%s" % t for t in tags)
    exact, fuzzy = [], []
    for el in d.find_elements(By.XPATH, "//*[%s]" % xp):
        try:
            t = (el.text or "").strip()
        except Exception:
            continue
        if not t or len(t) > 40:
            continue
        if t == text:
            exact.append(el)
        elif text in t:
            fuzzy.append(el)
    for el in (exact + fuzzy):
        try:
            d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.click()
            return True
        except Exception:
            try:
                d.execute_script("arguments[0].click();", el)
                return True
            except Exception:
                continue
    return False
