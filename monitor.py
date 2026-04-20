#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
富途牛牛模拟组合持仓监控
- 通过 portfolio.futunn.com 公开 API 获取模拟组合持仓
- 支持双通道推送：钉钉（加签 markdown）+ Discord（embed + ASCII 表格）
  两个都可以配，同时推送；任选其一也可。

注意：API 要求请求源 IP 在中国大陆或香港，海外 IP 会被风控拦截（code=-12009）
"""

import os
import sys
import time
import json
import hmac
import hashlib
import base64
import urllib.parse
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv()

PORTFOLIO_IDS = os.getenv("PORTFOLIO_IDS", "")

# 钉钉（加签）
DINGTALK_WEBHOOK = os.getenv("DINGTALK_WEBHOOK", "")
DINGTALK_SECRET = os.getenv("DINGTALK_SECRET", "")

# Discord
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "36"))
CHANGE_THRESHOLD = float(os.getenv("CHANGE_THRESHOLD", "2.0"))

API_URL = "https://portfolio.futunn.com/portfolio-api/get-portfolio-position"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://portfolio.futunn.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

PORTFOLIO_NAMES = {}
previous_positions = {}

session = requests.Session()
session.headers.update(HEADERS)


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# ========== 富途 API ==========

def get_portfolio_positions(portfolio_id):
    params = {"portfolio_id": portfolio_id, "language": 0}
    try:
        resp = session.get(API_URL, params=params, timeout=15)
        data = resp.json()
        if data.get("code") == 0:
            result = data.get("data", {})
            portfolio_name = result.get("portfolio_name", f"组合{portfolio_id}")
            PORTFOLIO_NAMES[portfolio_id] = PORTFOLIO_NAMES.get(portfolio_id) or portfolio_name
            positions = {}
            for item in result.get("record_items", []):
                code = item.get("stock_code", "")
                name = item.get("stock_name", "")
                ratio = item.get("position_ratio", 0)
                weight = ratio / 10000000.0
                cost = item.get("cost_price", 0) / 1e9 if item.get("cost_price") else 0
                current = item.get("current_price", 0) / 1e9 if item.get("current_price") else 0
                positions[code] = {
                    "name": name,
                    "code": code,
                    "weight": weight,
                    "cost_price": cost,
                    "current_price": current,
                    "profit_pct": item.get("profit_and_loss_ratio", 0) / 10000000.0,
                }
            return positions
        else:
            log(f"API错误 组合{portfolio_id}: code={data.get('code')} msg={data.get('message', 'unknown')}")
            return None
    except Exception as e:
        log(f"请求异常 组合{portfolio_id}: {e}")
        return None


# ========== 钉钉推送 ==========

def gen_dingtalk_sign():
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{DINGTALK_SECRET}"
    hmac_code = hmac.new(
        DINGTALK_SECRET.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return timestamp, sign


def send_dingtalk(title, markdown_text):
    if not DINGTALK_WEBHOOK or not DINGTALK_SECRET:
        return False
    try:
        timestamp, sign = gen_dingtalk_sign()
        url = f"{DINGTALK_WEBHOOK}&timestamp={timestamp}&sign={sign}"
        payload = {"msgtype": "markdown", "markdown": {"title": title, "text": markdown_text}}
        resp = requests.post(url, json=payload, timeout=10)
        result = resp.json()
        if result.get("errcode") == 0:
            log(f"钉钉推送成功: {title}")
            return True
        else:
            log(f"钉钉推送失败: {result}")
            return False
    except Exception as e:
        log(f"钉钉推送异常: {e}")
        return False


# ========== Discord 推送 ==========

def send_discord(title, description, color=0xff9900):
    if not DISCORD_WEBHOOK:
        return False
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": "Futunn Portfolio Monitor"},
    }
    payload = {"embeds": [embed]}
    try:
        resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
        if resp.status_code == 204:
            log(f"Discord 推送成功: {title}")
            return True
        else:
            log(f"Discord 推送失败: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        log(f"Discord 推送异常: {e}")
        return False


def send_notification(title, dingtalk_markdown, discord_description, color=0xff9900):
    """统一入口：向已配置的通道推送"""
    send_dingtalk(title, dingtalk_markdown)
    send_discord(title, discord_description, color)


# ========== 对比逻辑 ==========

def compare_positions(portfolio_id, old_pos, new_pos):
    changes = []
    all_codes = set(list(old_pos.keys()) + list(new_pos.keys()))
    for code in all_codes:
        if code in new_pos and code not in old_pos:
            info = new_pos[code]
            cost_str = f"${info['cost_price']:.2f}" if info['cost_price'] else "N/A"
            curr_str = f"${info['current_price']:.2f}" if info['current_price'] else "N/A"
            changes.append({
                "type": "新增", "name": info['name'], "code": code,
                "old_weight": 0, "new_weight": info['weight'],
                "cost": cost_str, "current": curr_str,
            })
        elif code in old_pos and code not in new_pos:
            info = old_pos[code]
            cost_str = f"${info['cost_price']:.2f}" if info['cost_price'] else "N/A"
            curr_str = f"${info['current_price']:.2f}" if info['current_price'] else "N/A"
            changes.append({
                "type": "清仓", "name": info['name'], "code": code,
                "old_weight": info['weight'], "new_weight": 0,
                "cost": cost_str, "current": curr_str,
            })
        else:
            old_weight = old_pos[code]["weight"]
            new_weight = new_pos[code]["weight"]
            diff = abs(new_weight - old_weight)
            if diff >= CHANGE_THRESHOLD:
                direction = "加仓" if new_weight > old_weight else "减仓"
                info = new_pos[code]
                cost_str = f"${info['cost_price']:.2f}" if info['cost_price'] else "N/A"
                curr_str = f"${info['current_price']:.2f}" if info['current_price'] else "N/A"
                changes.append({
                    "type": direction, "name": info['name'], "code": code,
                    "old_weight": old_weight, "new_weight": new_weight,
                    "cost": cost_str, "current": curr_str,
                })
    return changes


# ========== 格式化 ==========

def _ascii_table(headers, rows):
    """给 Discord 用的 ASCII 对齐表格"""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    def fmt(cells):
        return " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(cells))

    lines = [fmt(headers), "-" * (sum(col_widths) + 3 * (len(headers) - 1))]
    for r in rows:
        lines.append(fmt(r))
    return "\n".join(lines)


def build_dingtalk_markdown(portfolio_name, changes, positions):
    """钉钉 markdown 表格"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    emoji_map = {"新增": "🆕", "清仓": "🗑️", "加仓": "⬆️", "减仓": "⬇️"}
    lines = [f"## 📊 {portfolio_name} 调仓通知\n"]
    lines.append(f"**时间**: {now}　|　**阈值**: {CHANGE_THRESHOLD}%\n")

    lines.append("### 🔔 调仓变动")
    lines.append("| 类型 | 名称 | 代码 | 仓位变化 | 成本价 | 当前价 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for c in changes:
        emoji = emoji_map.get(c["type"], "•")
        if c["type"] == "清仓":
            wc = f"{c['old_weight']:.1f}% → 0%"
        elif c["type"] == "新增":
            wc = f"0% → {c['new_weight']:.1f}%"
        else:
            wc = f"{c['old_weight']:.1f}% → {c['new_weight']:.1f}%"
        lines.append(f"| {emoji}{c['type']} | {c['name']} | {c['code']} | {wc} | {c['cost']} | {c['current']} |")

    lines.append("\n### 📋 当前持仓")
    lines.append("| 代码 | 名称 | 仓位 | 成本价 | 当前价 | 盈亏 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for code, info in sorted(positions.items(), key=lambda x: x[1]['weight'], reverse=True):
        cost_str = f"${info['cost_price']:.2f}" if info['cost_price'] else "N/A"
        curr_str = f"${info['current_price']:.2f}" if info['current_price'] else "N/A"
        if info['profit_pct'] >= 0:
            profit_str = f"🟢 +{info['profit_pct']:.1f}%"
        else:
            profit_str = f"🔴 {info['profit_pct']:.1f}%"
        lines.append(f"| {code} | {info['name']} | {info['weight']:.1f}% | {cost_str} | {curr_str} | {profit_str} |")
    return "\n".join(lines)


def build_discord_description(portfolio_name, changes, positions):
    """Discord embed description：ASCII 表格（因 Discord 不支持 markdown 表格）"""
    sections = []

    # 调仓变动
    sections.append("**调仓变动**")
    change_headers = ["类型", "名称", "代码", "仓位变化", "成本", "当前"]
    change_rows = []
    for c in changes:
        if c["type"] == "清仓":
            wc = f"{c['old_weight']:.1f}%→0%"
        elif c["type"] == "新增":
            wc = f"0%→{c['new_weight']:.1f}%"
        else:
            wc = f"{c['old_weight']:.1f}%→{c['new_weight']:.1f}%"
        change_rows.append([c["type"], c["name"], c["code"], wc, c["cost"], c["current"]])
    sections.append("```\n" + _ascii_table(change_headers, change_rows) + "\n```")

    # 当前持仓
    sections.append("**当前持仓**")
    hold_headers = ["代码", "仓位", "成本", "当前", "盈亏"]
    hold_rows = []
    for code, info in sorted(positions.items(), key=lambda x: x[1]['weight'], reverse=True):
        cost_str = f"${info['cost_price']:.2f}" if info['cost_price'] else "N/A"
        curr_str = f"${info['current_price']:.2f}" if info['current_price'] else "N/A"
        profit_str = f"+{info['profit_pct']:.1f}%" if info['profit_pct'] >= 0 else f"{info['profit_pct']:.1f}%"
        hold_rows.append([code, f"{info['weight']:.1f}%", cost_str, curr_str, profit_str])
    sections.append("```\n" + _ascii_table(hold_headers, hold_rows) + "\n```")

    return "\n".join(sections)


# ========== 主循环 ==========

def check_all_portfolios():
    global previous_positions
    ids = [pid.strip() for pid in PORTFOLIO_IDS.split(",") if pid.strip()]
    for pid in ids:
        positions = get_portfolio_positions(pid)
        if positions is None:
            continue
        portfolio_name = PORTFOLIO_NAMES.get(pid, f"组合{pid}")
        if pid not in previous_positions:
            previous_positions[pid] = positions
            log(f"初始化 {portfolio_name} ({pid}): {len(positions)}个持仓")
            continue
        changes = compare_positions(pid, previous_positions[pid], positions)
        if changes:
            log(f"{portfolio_name} 发现 {len(changes)} 个变动")
            for c in changes:
                log(f"  {c}")
            title = f"📊 {portfolio_name} 调仓通知"
            dt_msg = build_dingtalk_markdown(portfolio_name, changes, positions)
            dc_msg = build_discord_description(portfolio_name, changes, positions)
            send_notification(title, dt_msg, dc_msg, color=0xff9900)
        previous_positions[pid] = positions
        time.sleep(1)


def main():
    log("=" * 50)
    log("富途组合监控启动")
    log(f"监控组合: {PORTFOLIO_IDS}")
    log(f"检查间隔: {CHECK_INTERVAL}秒")
    log(f"变化阈值: {CHANGE_THRESHOLD}%")
    channels = []
    if DINGTALK_WEBHOOK and DINGTALK_SECRET:
        channels.append("钉钉")
    if DISCORD_WEBHOOK:
        channels.append("Discord")
    log(f"推送通道: {', '.join(channels) if channels else '无（警告：未配置任何推送）'}")
    log("=" * 50)

    if not PORTFOLIO_IDS:
        log("错误：未配置 PORTFOLIO_IDS")
        sys.exit(1)
    if not channels:
        log("错误：至少配置一个推送通道（钉钉 或 Discord）")
        sys.exit(1)

    startup_dt = (
        f"## 🟢 富途组合监控已启动\n\n"
        f"- 监控组合数: **{len(PORTFOLIO_IDS.split(','))}**\n"
        f"- 检查间隔: **{CHECK_INTERVAL}** 秒\n"
        f"- 变化阈值: **{CHANGE_THRESHOLD}%**\n"
        f"- 推送通道: **{', '.join(channels)}**\n"
        f"- 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    startup_dc = (
        f"正在监控 **{len(PORTFOLIO_IDS.split(','))}** 个组合\n"
        f"检查间隔: **{CHECK_INTERVAL}** 秒\n"
        f"变化阈值: **{CHANGE_THRESHOLD}%**"
    )
    send_notification("🟢 富途组合监控已启动", startup_dt, startup_dc, color=0x00ff00)

    while True:
        try:
            check_all_portfolios()
        except Exception as e:
            log(f"检查异常: {e}")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
