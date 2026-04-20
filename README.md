# 富途牛牛模拟组合监控

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://www.docker.com/)

监控富途牛牛 APP 中社区模拟组合的持仓变动，推送完整的 Markdown/ASCII 表格通知（调仓变动 + 当前持仓 + 成本价/当前价/盈亏）。

**支持双推送通道：钉钉（加签）+ Discord**，两个可以同时配、也可以只配一个。

---

## ✨ 特性

- 🔄 **无需登录富途账户**，直接调用公开 API
- 📊 **完整表格推送**：调仓类型、名称、代码、仓位变化、成本价、当前价、盈亏一目了然
- 📨 **双通道推送**：钉钉（加签 markdown 表格）+ Discord（embed + ASCII 对齐表格），同时配置则同时推送
- ⚡ **秒级检测**：默认 36 秒轮询一次
- 🎯 **智能阈值**：权重变化 < 2% 不推送（可配置），新增/清仓始终推送
- 🐳 **Docker 就绪**：一行命令拉起
- 🛡️ **稳定运行**：systemd / launchd / 任务计划程序 / Docker restart 策略全覆盖

## 🖼️ 推送效果

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

| 出口 IP | 富途 API | Discord 推送 | 钉钉推送 |
|---|---|---|---|
| 🇨🇳 中国大陆 | ✅ | ❌（被墙）| ✅ |
| 🇭🇰 香港 | ✅ | ✅ | ✅ |
| 🇸🇬 新加坡 / 🇺🇸 美国 | ❌ | ✅ | ✅ |

**推荐部署环境：**
- 若你想用 **Discord**：选 **香港**服务器（同时能用钉钉）
- 若只用 **钉钉**：中国大陆或香港服务器都行
- Mac/Windows 本机：保持网络在大陆或香港（不要挂海外 VPN）

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/zhaochunyuan/futunn-portfolio-monitor.git
cd futunn-portfolio-monitor
```

### 2. 创建推送渠道（任选其一或全选）

**钉钉机器人（加签）：**
1. 钉钉群 → 群设置 → **智能群助手** → **添加机器人** → **自定义**
2. 安全设置选 **加签**（不要选关键词或IP白名单）
3. 复制 **Webhook** 和 **加签密钥**

**Discord Webhook：**
1. Discord 服务器 → 频道右键 → **编辑频道** → **整合** → **Webhook**
2. 新建 Webhook → 复制 URL

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 PORTFOLIO_IDS、钉钉和/或 Discord 配置
```

### 4. 选择部署方式

- [🐳 Docker（推荐，最简单）](#-docker-部署推荐)
- [🐧 Linux（systemd 服务）](#-linux-systemd-部署)
- [🍎 macOS（launchd）](#-macos-部署)
- [🪟 Windows（任务计划）](#-windows-部署)

---

## 🐳 Docker 部署（推荐）

最简单的部署方式，一条命令拉起。

### 前置要求

- 安装 [Docker](https://docs.docker.com/get-docker/) 和 [Docker Compose](https://docs.docker.com/compose/install/)
- 已创建 `.env` 文件

### 启动

```bash
docker compose up -d
```

首次会自动构建镜像（约 1-2 分钟），之后立即启动。启动成功后，配置的推送渠道会收到"监控已启动"消息。

### 常用命令

| 操作 | 命令 |
|---|---|
| 查看实时日志 | `docker compose logs -f` |
| 查看状态 | `docker compose ps` |
| 重启 | `docker compose restart` |
| 停止 | `docker compose down` |
| 修改配置后重启 | 编辑 `.env` → `docker compose up -d` |
| 重新构建镜像 | `docker compose build --no-cache` |

### 直接用 docker run（不用 compose）

```bash
docker build -t futunn-monitor .
docker run -d \
  --name futunn-monitor \
  --restart unless-stopped \
  --env-file .env \
  futunn-monitor
```

### 数据持久化

当前版本的持仓快照只存在内存中，容器重启后会重新初始化（首次无推送，第二次起检测变化）。如果需要跨重启保留，可自行挂载 volume 并改造代码把 `previous_positions` 持久化到文件。

---

## 🐧 Linux systemd 部署

适合 VPS，开机自启 + 崩溃自动重启。推荐 Ubuntu 22.04 / 24.04。

```bash
# 1. 放到标准路径
sudo mkdir -p /opt/futunn_monitor
sudo cp monitor.py .env /opt/futunn_monitor/
cd /opt/futunn_monitor
sudo python3 -m venv venv
sudo ./venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r /path/to/requirements.txt

# 2. 安装 systemd 服务
sudo cp futunn-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now futunn-monitor

# 3. 查看状态 / 日志
sudo systemctl status futunn-monitor
sudo journalctl -u futunn-monitor -f
```

| 操作 | 命令 |
|---|---|
| 启动 | `sudo systemctl start futunn-monitor` |
| 停止 | `sudo systemctl stop futunn-monitor` |
| 重启 | `sudo systemctl restart futunn-monitor` |
| 查看日志 | `sudo journalctl -u futunn-monitor -f` |
| 修改配置后重启 | `sudo vim /opt/futunn_monitor/.env && sudo systemctl restart futunn-monitor` |

---

## 🍎 macOS 部署

### 前台运行（测试）

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python monitor.py
```

### 后台常驻（launchd）

创建 `~/Library/LaunchAgents/com.futunn.monitor.plist`：

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

---

## 🪟 Windows 部署

### 1. 安装 Python

从 [python.org](https://www.python.org/downloads/windows/) 下载 Python 3.12，安装时**勾选 "Add Python to PATH"**。

### 2. 初始化

```cmd
cd D:\futunn-portfolio-monitor
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env  :: 编辑配置
```

### 3. 启动脚本 `start.bat`

```bat
@echo off
chcp 65001 >nul
cd /d %~dp0
venv\Scripts\python.exe monitor.py
pause
```

### 4. 开机自启（任务计划程序）

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
├── monitor.py                 # 主脚本
├── .env.example               # 配置模板
├── requirements.txt           # Python 依赖
├── Dockerfile                 # Docker 镜像定义
├── docker-compose.yml         # Docker Compose 编排
├── .dockerignore
├── futunn-monitor.service     # Linux systemd 服务模板
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
| `DINGTALK_WEBHOOK` | ⭕ | - | 钉钉机器人 Webhook（和 Discord 至少配一个） |
| `DINGTALK_SECRET` | ⭕ | - | 钉钉加签密钥（SEC 开头） |
| `DISCORD_WEBHOOK` | ⭕ | - | Discord Webhook URL |
| `CHECK_INTERVAL` | ❌ | 36 | 检查间隔秒数 |
| `CHANGE_THRESHOLD` | ❌ | 2.0 | 权重变化阈值（百分点） |

> ⭕ = 钉钉和 Discord 至少配置一个，两个都配则同时推送。

---

## 🔧 API 说明

### 数据接口

```
GET https://portfolio.futunn.com/portfolio-api/get-portfolio-position?portfolio_id={id}&language=0
```

**必须的请求头：**
```
User-Agent: Mozilla/5.0 ...
Referer: https://portfolio.futunn.com/
Accept: application/json
Accept-Language: zh-CN,zh;q=0.9
```

**返回字段（关键）：**
- `code`：0 成功，`-12009` = IP 风控
- `data.portfolio_name`：组合名称
- `data.record_items[]`：持仓列表
  - `stock_code`, `stock_name`：股票代码/名称
  - `position_ratio`：仓位比例（÷ 10^7 得百分比）
  - `cost_price`, `current_price`：价格（÷ 10^9）
  - `profit_and_loss_ratio`：盈亏比例（÷ 10^7）

---

## 🐛 故障排查

<details>
<summary><b>API 返回 <code>{"code":-12009}</code></b></summary>

出口 IP 在富途黑名单（海外 IP 基本都被拒）。换中国大陆或香港的服务器/网络。
</details>

<details>
<summary><b>钉钉推送失败 <code>errcode: 310000</code></b></summary>

检查机器人安全设置是否选的"加签"，密钥是否以 `SEC` 开头。
</details>

<details>
<summary><b>Discord 推送超时或 403</b></summary>

- 中国大陆服务器无法访问 Discord（需要海外或香港服务器/代理）
- 检查 Webhook URL 是否完整（含 `/webhooks/ID/TOKEN`）
- Webhook 被删除或 token 失效也会 403/404
</details>

<details>
<summary><b>Docker 容器启动失败</b></summary>

```bash
docker compose logs     # 看启动错误
docker compose down && docker compose up -d --build   # 重新构建
```

常见原因：`.env` 文件缺失、`PORTFOLIO_IDS` 没填、推送渠道都没配置。
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

- 权重变化 < `CHANGE_THRESHOLD`（默认 2.0%）→ 调小阈值
- 首次运行只初始化，第二轮开始才检测变化
- 调仓后又被调回，两次检查间隙未捕获
</details>

---

## 📝 License

[MIT](LICENSE)

## ⚠️ 免责声明

本项目仅用于个人学习和研究，监控数据来自富途社区公开的模拟组合。请遵守富途服务条款，不要高频轮询（建议 ≥ 30 秒一次）。使用本项目导致的任何后果由使用者自行承担。
