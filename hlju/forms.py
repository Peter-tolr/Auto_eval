# -*- coding: utf-8 -*-
"""问卷页面（#/survery/children/surverySubmit/...）的解析与填写。"""
from __future__ import annotations

import random
import time

from selenium.webdriver.common.by import By

from . import browser as B
from . import scoring


def question_blocks(d):
    return d.find_elements(By.CSS_SELECTOR, "div#demo")


def read_blocks(d):
    """返回 [(题干, 选项文本列表, 是否有文本框)]"""
    out = []
    for blk in question_blocks(d):
        try:
            h4 = blk.find_element(By.TAG_NAME, "h4").text.strip()
        except Exception:
            h4 = ""
        labels = []
        for lab in blk.find_elements(By.CSS_SELECTOR, "label"):
            try:
                txt = " ".join((lab.text or "").split())
            except Exception:
                txt = ""
            labels.append(txt)
        has_text = bool(blk.find_elements(By.TAG_NAME, "textarea"))
        out.append((h4, labels, has_text))
    return out


def fill(d, comments: dict, rng: random.Random, dry_run: bool = False) -> dict:
    """填写当前问卷。返回统计信息。"""
    blocks = question_blocks(d)
    choice_blocks, text_blocks = [], []
    for i, blk in enumerate(blocks):
        if blk.find_elements(By.CSS_SELECTOR, "input[type=radio]"):
            choice_blocks.append((i, blk))
        elif blk.find_elements(By.TAG_NAME, "textarea"):
            text_blocks.append((i, blk))

    idx_plan = scoring.plan(len(choice_blocks), rng)
    chosen = []
    for (bi, blk), opt in zip(choice_blocks, idx_plan):
        labels = blk.find_elements(By.CSS_SELECTOR, "label")
        if not labels:
            continue
        opt = min(opt, len(labels) - 1)
        target = labels[opt]
        if not dry_run:
            try:
                target.click()
            except Exception:
                d.execute_script("arguments[0].click();", target)
            time.sleep(0.05)
        chosen.append(opt)

    # 主观题文本
    pos = comments.get("satisfied") or ["课程内容充实，老师讲解清晰，收获很大。"]
    neg = comments.get("improve") or ["希望课堂互动再多一些，增加案例讨论环节。"]
    texts = []
    for k, (bi, blk) in enumerate(text_blocks):
        txt = (rng.choice(pos) if k == 0 else rng.choice(neg))
        ta = blk.find_element(By.TAG_NAME, "textarea")
        if not dry_run:
            ta.clear()
            ta.send_keys(txt)
            time.sleep(0.1)
        texts.append(txt)

    # 校验是否都已选中
    selected = d.execute_script(
        "return Array.from(document.querySelectorAll('div#demo')).map(function(b){"
        "  var r=b.querySelector('input[type=radio]:checked');"
        "  var t=b.querySelector('textarea');"
        "  return r? r.value : (t? (t.value.length>0) : null); });")
    return {
        "questions": len(blocks),
        "choice": len(choice_blocks),
        "text": len(text_blocks),
        "plan": chosen,
        "texts": texts,
        "selected": selected,
    }


def submit(d) -> bool:
    """点击提交并确认弹窗。"""
    clicked = B.click_text(d, "提交", tags=("a", "button", "div", "span"))
    if not clicked:
        return False
    time.sleep(1.5)
    # Element UI 确认框优先点主按钮
    try:
        btn = d.find_elements(By.CSS_SELECTOR, ".el-message-box__btns .el-button--primary")
        if btn:
            btn[0].click()
        else:
            for kw in ("确定", "确认"):
                if B.click_text(d, kw, tags=("button", "span", "div", "a")):
                    break
    except Exception:
        pass
    time.sleep(2)
    return True
