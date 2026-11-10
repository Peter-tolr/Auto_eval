# -*- coding: utf-8 -*-
"""黑龙江大学 学生评教 自动填写脚本

用法：
    python pj.py                  # 交互选择账号后执行
    python pj.py -a 20240378      # 指定账号（账号在 accounts.json 里）
    python pj.py -a 20240378 --dry-run   # 只填写不提交
    python pj.py -a 20240378 --limit 1   # 只做 1 份
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hlju import config as C
from hlju import runner as R


def pick_account(accounts: dict) -> str:
    items = list(accounts.items())
    if not items:
        print("accounts.json 里没有账号，请先添加：{\"学号\": {\"password\": \"密码\"}}")
        sys.exit(2)
    if len(items) == 1:
        return items[0][0]
    print("请选择账号：")
    for i, (acc, info) in enumerate(items, 1):
        print("  %d. %s %s" % (i, acc, info.get("name", "")))
    while True:
        s = input("序号（回车=1）：").strip() or "1"
        if s.isdigit() and 1 <= int(s) <= len(items):
            return items[int(s) - 1][0]


def main() -> int:
    ap = argparse.ArgumentParser(description="黑龙江大学学生评教自动填写")
    ap.add_argument("-a", "--account", help="学号（需在 accounts.json 中）")
    ap.add_argument("-p", "--password", help="密码（不填则用 accounts.json 中的）")
    ap.add_argument("--limit", type=int, default=0, help="最多提交几份问卷，0=全部")
    ap.add_argument("--dry-run", action="store_true", help="只填写不提交")
    ap.add_argument("--headless", action="store_true", help="无头模式（不显示浏览器窗口）")
    ap.add_argument("--yes", action="store_true", help="跳过确认提示")
    ap.add_argument("--fresh", action="store_true", help="使用全新的浏览器配置目录（需重新登录）")
    ap.add_argument("--list", action="store_true", help="列出 accounts.json 中的账号")
    args = ap.parse_args()

    accounts = C.load_accounts()
    if args.list:
        for acc, info in accounts.items():
            print("%s\t%s" % (acc, info.get("name", "")))
        return 0

    account = args.account or pick_account(accounts)
    info = accounts.get(account, {})
    password = args.password or info.get("password") or ""
    if not password:
        import getpass
        password = getpass.getpass("请输入 %s 的统一身份认证密码：" % account)
    settings = C.load_settings()
    if args.fresh:
        settings["profile_dir"] = ".profiles/_fresh"
    comments = C.load_json("comments.json", {})

    print("=" * 56)
    print("账号：%s %s" % (account, info.get("name", "")))
    print("模式：%s" % ("试运行（不提交）" if args.dry_run else "正式提交"))
    print("上限：%s" % (args.limit or "全部"))
    print("=" * 56)
    if not args.yes and not args.dry_run:
        try:
            if input("确认开始？(Y/n) ").strip().lower() in ("n", "no"):
                print("已取消")
                return 0
        except EOFError:
            pass

    t0 = time.time()
    code = R.run(account, password, limit=args.limit, dry_run=args.dry_run,
                 headless=args.headless, settings=settings, comments=comments)
    print("用时 %.0f 秒，退出码 %d" % (time.time() - t0, code))
    return code


if __name__ == "__main__":
    sys.exit(main())