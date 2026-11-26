# -*- coding: utf-8 -*-
"""统一身份认证（SSO）+ 教学评价系统（zlpj）入口。

流程说明：直接打开评价系统，如果它把浏览器弹到统一身份认证页，就在那一页
用账号密码登录，CAS 会带着 ticket 跳回评价系统，SPA 随后自动换取登录态。
这样浏览器窗口不会先绕到“信息门户”。
"""
from __future__ import annotations

import time

from selenium.webdriver.common.by import By

from . import browser as B

SSO_HOST = "sso.hlju.edu.cn"
# 兜底入口：直接打开统一身份认证（service 指向信息门户）
SSO_ENTRY = "https://sso.hlju.edu.cn/cas/login?service=https%3A%2F%2Fxyw.hlju.edu.cn%2F"
APP_URL = "https://zlpj.hlju.edu.cn/static/vue/vue/"


def _pwd_tab(d):
    for el in d.find_elements(By.XPATH, "//*[self::div or self::span or self::li or self::a]"):
        try:
            if (el.text or "").strip() == "账号密码":
                return el
        except Exception:
            pass
    return None


def on_sso_page(d) -> bool:
    t = B.body_text(d)
    if "/cas/login" in d.current_url or SSO_HOST in d.current_url:
        return True
    return "账号密码" in t and "立即登录" in t


def app_rendered(d) -> bool:
    try:
        n = d.execute_script("var a=document.querySelector('#app'); return a? a.innerHTML.length : -1;")
    except Exception:
        n = -1
    return isinstance(n, int) and n > 200


def login_sso(d, user: str, password: str, timeout: float = 120) -> bool:
    """在当前 SSO 页用账号密码登录。成功返回 True（已离开 CAS）。"""
    if not B.wait_until(lambda: _pwd_tab(d) is not None, timeout=timeout, interval=2):
        return False
    tab = _pwd_tab(d)
    if tab is not None:
        try:
            tab.click()
            time.sleep(1.0)
        except Exception:
            pass
    try:
        u = d.find_element(By.CSS_SELECTOR,
                           "input[placeholder*='工号'], input[placeholder*='学号'], input[type='text']")
        p = d.find_element(By.CSS_SELECTOR, "input[type='password']")
    except Exception:
        return False
    u.clear(); u.send_keys(user)
    time.sleep(0.2)
    p.clear(); p.send_keys(password)
    time.sleep(0.3)
    btns = [b for b in d.find_elements(By.TAG_NAME, "button") if "登录" in (b.text or "")]
    if not btns:
        return False
    btns[0].click()
    for _ in range(30):
        time.sleep(2)
        if "二次" in B.body_text(d):
            return False
        if "/cas/login" not in d.current_url:
            return True
    return False


def open_app(d, user: str, password: str, timeout: float = 210) -> bool:
    """打开评价系统并确保已登录、SPA 已渲染。"""
    d.get(APP_URL)
    t0 = time.time()
    tried_login = 0
    while time.time() - t0 < timeout:
        time.sleep(2.5)
        if on_sso_page(d):
            if tried_login < 2:
                tried_login += 1
                login_sso(d, user, password, timeout=90)
                time.sleep(2)
                continue
            return False
        if app_rendered(d):
            # 等前端拿到登录态（用户名出现）
            B.wait_until(lambda: "未登录" not in B.body_text(d), timeout=60, interval=2)
            return True
    return False


def ensure_sso(d, user: str, password: str, timeout: float = 150) -> bool:
    """兜底：直接打开统一身份认证登录页完成登录。"""
    if app_rendered(d):
        return True
    d.get(SSO_ENTRY)
    return login_sso(d, user, password, timeout=timeout) if on_sso_page(d) else True
