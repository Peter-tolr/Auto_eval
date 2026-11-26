# -*- coding: utf-8 -*-
"""评教流程：登录 -> 打开问卷列表 -> 逐份填写并提交。"""
from __future__ import annotations

import json
import os
import random
import time
import traceback
from datetime import datetime

from . import browser as B
from . import forms as F
from . import login as L

HERE = B.HERE
LOG_DIR = os.path.join(HERE, "logs")


class Logger:
    def __init__(self, account: str):
        os.makedirs(LOG_DIR, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(LOG_DIR, "%s_%s.jsonl" % (account, stamp))
        self.fh = open(self.path, "a", encoding="utf-8")

    def log(self, **kw):
        kw["ts"] = datetime.now().isoformat(timespec="seconds")
        line = json.dumps(kw, ensure_ascii=False, default=str)
        self.fh.write(line + "\n")
        self.fh.flush()
        msg = kw.get("msg")
        if msg:
            print("  " + str(msg))

    def close(self):
        try:
            self.fh.close()
        except Exception:
            pass


def open_survey_list(d, timeout: float = 90) -> bool:
    """进入“学生评教”问卷列表（优先直接跳转路由）。"""
    if progress(d) is not None:
        return True
    # 直接跳 hash 路由，最稳
    try:
        d.execute_script("window.location.hash = '#/survery?isShowMerge=1&isLimitTeaScore=1&k=1';")
    except Exception:
        pass
    if B.wait_until(lambda: progress(d) is not None, timeout=45, interval=2):
        return True
    # 备用一：首页「去完成」
    if B.click_text(d, "去完成"):
        if B.wait_until(lambda: "/survery" in d.current_url, timeout=timeout, interval=2):
            B.wait_until(lambda: progress(d) is not None, timeout=30, interval=1)
            if progress(d) is not None:
                return True
    # 备用二：应用列表 -> 学生评教
    d.execute_script("""var els=document.querySelectorAll('.el-submenu__title');
        for(var i=0;i<els.length;i++){ if(els[i].innerText.indexOf('应用列表')>=0){ els[i].click(); break; } }""")
    time.sleep(1.5)
    d.execute_script("""var els=document.querySelectorAll('.el-menu-item');
        for(var i=0;i<els.length;i++){ if(els[i].innerText.indexOf('学生评教')>=0){ els[i].click(); break; } }""")
    return B.wait_until(lambda: progress(d) is not None, timeout=timeout, interval=2)


def remaining(d) -> int:
    try:
        return len([e for e in d.find_elements("xpath", "//*[normalize-space(text())='去填写']")])
    except Exception:
        return -1


def progress(d):
    """从页面文字解析 (应评总数, 已评数)；解析失败返回 None。"""
    import re as _re
    t = B.body_text(d)
    m1 = _re.search(r"本学期应评[:：]?\s*(\d+)", t)
    m2 = _re.search(r"已评问卷数[:：]?\s*(\d+)", t)
    if not m1 or not m2:
        return None
    return int(m1.group(1)), int(m2.group(1))


def form_title(d) -> str:
    try:
        return d.execute_script("var e=document.querySelector('.drop-title'); return e? e.innerText.trim() : ''") or ""
    except Exception:
        return ""


def validate(d) -> tuple[bool, str]:
    """检查是否所有题目都已作答。"""
    problems = d.execute_script("""
      var out=[];
      Array.from(document.querySelectorAll('div#demo')).forEach(function(b,i){
        var r=b.querySelector('input[type=radio]');
        var t=b.querySelector('textarea');
        if(r){ if(!b.querySelector('input[type=radio]:checked')) out.push('Q'+(i+1)+' 未选'); }
        else if(t){ if(!t.value.trim()) out.push('Q'+(i+1)+' 未填'); }
      });
      return out;""")
    if problems:
        return False, "；".join(problems[:5])
    return True, ""


def run(account: str, password: str, limit: int = 0, dry_run: bool = False,
        headless: bool = False, settings: dict | None = None, comments: dict | None = None) -> int:
    settings = settings or {}
    comments = comments or {}
    profile = os.path.join(HERE, settings.get("profile_dir", ".profiles"), account)
    os.makedirs(profile, exist_ok=True)
    logger = Logger(account)
    done = 0
    d = None
    try:
        logger.log(event="start", account=account, limit=limit, dry_run=dry_run)
        d = B.launch(profile, headless=headless)
        if not L.open_app(d, account, password):
            logger.log(event="warn", msg="首轮打开失败，改用统一身份认证页重试")
            if not L.ensure_sso(d, account, password) or not L.open_app(d, account, password):
                logger.log(event="error", msg="登录或打开教学评价系统失败（可能需要二次验证，见截图）")
                B.screenshot(d, "err_sso")
                return 2
        logger.log(event="sso_ok", msg="已登录教学评价系统")
        if not B.wait_until(lambda: "翟浩男" in B.body_text(d) or "未登录" not in B.body_text(d), timeout=90, interval=2):
            logger.log(event="warn", msg="等待登录态超时，继续尝试")
        logger.log(event="app_ready")
        if not open_survey_list(d):
            logger.log(event="error", msg="无法进入问卷列表")
            B.screenshot(d, "err_list")
            return 3
        B.wait_until(lambda: progress(d) is not None, timeout=30, interval=1)
        p = progress(d) or (0, 0)
        B.screenshot(d, "list_ready")
        logger.log(event="list_ready", total=p[0], evaluated=p[1],
                   msg="本学期应评 %d 份，已评 %d 份" % p)

        while True:
            if limit and done >= limit:
                logger.log(event="limit_reached", done=done)
                break
            p = progress(d)
            if p is not None and p[0] > 0 and p[1] >= p[0]:
                logger.log(event="all_done", total=p[0], evaluated=p[1], msg="全部问卷已完成")
                break
            if p is None or remaining(d) <= 0:
                # 列表可能仍在渲染，稍等再判断一次
                if not B.wait_until(lambda: (progress(d) or (0, 0))[1] < (progress(d) or (0, 0))[0]
                                    or remaining(d) > 0, timeout=15, interval=1):
                    logger.log(event="all_done", msg="没有可填写的问卷了")
                    break
            rng = random.Random()
            seed = rng.randrange(1, 10**9)
            rng.seed(seed)
            if not B.click_text(d, "去填写"):
                logger.log(event="error", msg="找不到“去填写”按钮")
                break
            if not B.wait_until(lambda: "surverySubmit" in d.current_url, timeout=60, interval=2):
                logger.log(event="error", msg="问卷页面未打开")
                B.screenshot(d, "err_form_open")
                break
            time.sleep(2)
            title = form_title(d)
            info = F.fill(d, comments, rng, dry_run=dry_run)
            ok, why = validate(d) if not dry_run else (True, "")
            logger.log(event="filled", title=title, seed=seed, plan=info["plan"],
                       questions=info["questions"], choice=info["choice"], text=info["text"],
                       valid=ok, reason=why, msg="已填写：%s（%d 题，seed=%d）" % (title or "(无标题)", info["questions"], seed))
            B.screenshot(d, "form_%02d_filled" % (done + 1))
            if not ok:
                logger.log(event="error", msg="存在未作答题目，跳过提交：%s" % why)
                B.dump_html(d, "form_incomplete_%02d" % (done + 1))
                break
            if dry_run:
                logger.log(event="dry_run", msg="dry-run：不提交，仅演示")
                done += 1
                break
            if not F.submit(d):
                logger.log(event="error", msg="点击提交失败")
                B.screenshot(d, "err_submit")
                break
            back = B.wait_until(lambda: "/survery" in d.current_url and "surverySubmit" not in d.current_url,
                                timeout=25, interval=2)
            logger.log(event="submitted", title=title, back=back,
                       msg="提交完成：%s" % (title or "(无标题)"))
            B.screenshot(d, "form_%02d_submitted" % (done + 1))
            done += 1
            if not back:
                # 尝试点返回
                try:
                    d.execute_script("var e=document.querySelector('.x-header-back-icon'); if(e) e.click();")
                    time.sleep(3)
                except Exception:
                    pass
            time.sleep(float(settings.get("delay_between_forms", 3)))
        logger.log(event="finish", done=done, remaining=remaining(d),
                   msg="完成 %d 份，剩余 %d 份" % (done, remaining(d)))
        return 0
    except Exception:
        tb = traceback.format_exc()
        logger.log(event="exception", traceback=tb)
        print(tb)
        if d is not None:
            B.screenshot(d, "err_exception")
        return 1
    finally:
        logger.close()
        if d is not None:
            try:
                d.quit()
            except Exception:
                pass