# 富途牛牛模拟组合监控（钉钉推送版）

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)

监控富途牛牛 APP 中社区模拟组合的持仓变动，通过**钉钉机器人**推送完整的 Markdown 表格通知（调仓变动 + 当前持仓 + 成本价/当前价/盈亏）。

---

## ✨ 特性

- 🔄 **无需登录富途账户**，直接调用公开 API
- 📊 **完整表格推送**：调仓类型、名称、代码、仓位变化、成本价、当前价、盈亏一目了然
- ⚡ **秒级检测**：默认 36 秒轮询一次
- 🎯 **智能阈值**：权重变化 < 2% 不推送（可配置），新增/清仓始终推送
- 🛡️ **稳定运行**：systemd / launchd / 任务计划程序支持开机自启、崩溃重启
- 📱 **钉钉原生**：加签模式，表格清晰，手机和 PC 端都能正常显示

## 🖼️ 效果预览

推送的钉钉消息包含两个表格：

**调仓变动表：**

| 类型 | 名称 | 代码 | 仓位变化 | 成本价 | 当前价 |
|---|---|---|---|---|---|
| ⬆️加仓 | Apple | AAPL | 15.0% → 20.0% | $180.00 | $195.50 |
| 🆕新增 | Nvidia | NVDA | 0% → 8.0% | $420.00 | $430.25 |

**当前持仓表：**

| 代码 | 名称 | 仓位 | 成本价 | 当前价 | 盈亏 |
|---|---|---|---|---|---|
| AAPL | Apple | 20.0% | $180.00 | $195.50 | 🟢 +8.6% |
| NVDA | Nvidia | 8.0% | $420.00 | $430.25 | 🟢 +2.4% |

---

## ⚠️ 重要前置条件

### API 对请求源 IP 有地理限制

`portfolio.futunn.com` 的 API **只对中国大陆和香港 IP 开放**。海外 IP（新加坡、美国、日本等）会被风控拦截，返回 `{"code":-12009}`。

**实测结果：**

| 出口 IP | 结果 |
|---|---|
| 🇨🇳 中国大陆（上海） | ✅ `code:0` 返回完整数据 |
| 🇭🇰 香港 | ✅ 正常 |
| 🇸🇬 新加坡 | ❌ `code:-12009` |
| 🇺🇸 美国 | ❌ 被风控 |

**推荐部署环境：**
- 腾讯云/阿里云**香港**轻量服务器（能访问钉钉 + Discord，¥24-30/月）
- 腾讯云/阿里云**大陆**轻量服务器（只能访问钉钉，¥24/月起）
- 中国大陆或香港家用网络的 Mac/Windows 电脑

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/futunn-portfolio-monitor.git
cd futunn-portfolio-monitor
```

### 2. 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

# 国内推荐清华镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### 3. 创建钉钉机器人

1. 钉钉群 → 群设置 → **智能群助手** → **添加机器人** → **自定义**
2. 安全设置选 **加签**（不要选关键词或IP白名单）
3. 复制 **Webhook** 和 **加签密钥**

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的钉钉 Webhook、Secret、组合 ID
```

组合 ID 从富途 APP 的模拟组合分享链接里获取，URL 里的 `portfolio_id=XXXXXX`。

### 5. 运行

```bash
python monitor.py
```

启动成功后，钉钉群会收到"富途组合监控已启动"通知。按 Ctrl+C 停止。

---

## 🐧 Linux 生产部署（systemd）

推荐 Ubuntu 22.04 / 24.04，配合 systemd 实现开机自启、崩溃自动重启。

```bash
# 1. 放到标准路径
sudo mkdir -p /opt/futunn_monitor
sudo cp monitor.py .env /opt/futunn_monitor/
cd /opt/futunn_monitor
sudo python3 -m venv venv
sudo ./venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 2. 安装 systemd 服务
sudo cp futunn-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now futunn-monitor

# 3. 查看状态 / 日志
sudo systemctl status futunn-monitor
sudo journalctl -u futunn-monitor -f
```

常用命令：

| 操作 | 命令 |
|---|---|
| 启动 | `sudo systemctl start futunn-monitor` |
| 停止 | `sudo systemctl stop futunn-monitor` |
| 重启 | `sudo systemctl restart futunn-monitor` |
| 查看日志 | `sudo journalctl -u futunn-monitor -f` |
| 修改配置后重启 | `sudo vim /opt/futunn_monitor/.env && sudo systemctl restart futunn-monitor` |

---

## 🍎 macOS 部署

### 前台运行（测试用）

```bash
python monitor.py
```

### 后台常驻（launchd，开机自启）

创建 `~/Library/LaunchAgents/com.futunn.monitor.plist`，参考 [launchd 官方文档](https://www.launchd.info/)。示例：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.futunn.monitor</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/YOUR_USERNAME/futunn-portfolio-monitor/venv/bin/python</string>
    <string>/Users/YOUR_USERNAME/futunn-portfolio-monitor/monitor.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/YOUR_USERNAME/futunn-portfolio-monitor</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key>
  <string>/Users/YOUR_USERNAME/futunn-portfolio-monitor/monitor.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/YOUR_USERNAME/futunn-portfolio-monitor/monitor.log</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.futunn.monitor.plist
launchctl start com.futunn.monitor
```

卸载：
```bash
launchctl unload ~/Library/LaunchAgents/com.futunn.monitor.plist
```

---

## 🪟 Windows 部署

### 1. 安装 Python

从 [python.org](https://www.python.org/downloads/windows/) 下载 Python 3.12 安装包，安装时**勾选 "Add Python to PATH"**。

### 2. 项目初始化

打开 `cmd` 或 PowerShell：

```cmd
cd D:\futunn-portfolio-monitor
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 编辑 `.env`（复制 `.env.example` 重命名）

### 4. 创建启动脚本 `start.bat`

```bat
@echo off
chcp 65001 >nul
cd /d %~dp0
venv\Scripts\python.exe monitor.py
pause
```

双击即可运行。

### 5. 后台常驻（任务计划程序）

1. Win+R → `taskschd.msc` → 创建任务
2. 常规：勾选"不管用户是否登录都要运行"、"使用最高权限"
3. 触发器：新建 → 启动时
4. 操作：
   - 程序：`D:\futunn-portfolio-monitor\venv\Scripts\python.exe`
   - 参数：`monitor.py`
   - 起始位置：`D:\futunn-portfolio-monitor`
5. 设置：勾选"如果任务失败，重新启动"

---

## 📁 项目结构

```
futunn-portfolio-monitor/
├── monitor.py                 # 主监控脚本
├── .env.example               # 配置模板（复制为 .env 后填入真实值）
├── requirements.txt           # Python 依赖
├── futunn-monitor.service     # Linux systemd 服务定义
├── .gitignore
├── LICENSE
└── README.md
```

---

## ⚙️ 配置说明

所有配置通过 `.env` 文件管理：

| 变量 | 必需 | 默认 | 说明 |
|---|---|---|---|
| `PORTFOLIO_IDS` | ✅ | - | 组合 ID 列表，逗号分隔 |
| `DINGTALK_WEBHOOK` | ✅ | - | 钉钉机器人 Webhook URL |
| `DINGTALK_SECRET` | ✅ | - | 钉钉机器人加签密钥（SEC 开头） |
| `CHECK_INTERVAL` | ❌ | 36 | 检查间隔秒数，建议 30-60 |
| `CHANGE_THRESHOLD` | ❌ | 2.0 | 权重变化阈值（百分点） |

---

## 🔧 API 说明

### 数据接口

```
GET https://portfolio.futunn.com/portfolio-api/get-portfolio-position
```

**请求参数：**
- `portfolio_id`（必填）：组合 ID
- `language`：语言代码，`0` 为中文

**必须的请求头：**
```
User-Agent: Mozilla/5.0 ...
Referer: https://portfolio.futunn.com/
Accept: application/json
Accept-Language: zh-CN,zh;q=0.9
```

**返回字段（关键）：**
- `code`：0 成功，其他为错误码（`-12009` = IP 风控）
- `data.portfolio_name`：组合名称
- `data.record_items[]`：持仓列表
  - `stock_code`, `stock_name`：股票代码、名称
  - `position_ratio`：仓位比例（需除以 10^7 得百分比）
  - `cost_price`, `current_price`：价格（需除以 10^9）
  - `profit_and_loss_ratio`：盈亏比例（需除以 10^7）

---

## 🐛 故障排查

<details>
<summary><b>API 返回 <code>{"code":-12009}</code></b></summary>

**原因：** 出口 IP 在富途黑名单（海外 IP 基本都被拒）。

**解决：** 换到中国大陆或香港的服务器/网络。
</details>

<details>
<summary><b>钉钉推送失败 <code>errcode: 310000</code></b></summary>

**原因：** Webhook URL 或 Secret 错误，或加签模式不对。

**解决：** 检查机器人安全设置是否选的"加签"，密钥是否以 `SEC` 开头。
</details>

<details>
<summary><b><code>pip install</code> 卡住或失败</b></summary>

国内访问 pypi.org 慢。加清华镜像：
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```
</details>

<details>
<summary><b>调仓没推送</b></summary>

可能原因：
- 权重变化小于 `CHANGE_THRESHOLD`（默认 2.0%）→ 调小阈值
- 首次运行只初始化，第二轮开始才检测变化
- 调仓后又被调回，两次检查间隙未捕获
</details>

---

## 📝 License

[MIT](LICENSE)

## ⚠️ 免责声明

本项目仅用于个人学习和研究，监控数据来自富途社区公开的模拟组合。请遵守富途服务条款，不要高频轮询（建议 ≥ 30 秒一次）。使用本项目导致的任何后果由使用者自行承担。
