# spider

把微信公众号 / 知乎文章抓取到本地知识库的终端工具：正文清洗、图片本地化，可输出 **Markdown** 和**微信阅读模式 HTML**。

> 仅用于个人学习与资料归档。请遵守目标网站的服务条款与相关法律，不要用于侵犯他人权益的用途。

## 为什么需要它

- 微信文章正文容器默认带 `visibility: hidden; opacity: 0`，直接保存 HTML 会"没有内容"；现在渲染前会自动清洗，离线打开即可完整阅读。
- 图片会下载到文章目录的 `images/`，断网也能看。
- Markdown 带 YAML frontmatter，可直接进 Obsidian 知识库；HTML 保留公众号原有排版和图片。
- 支持微信「图片消息 / 分享页」：这类页面没有正文容器，工具会用页面里的摘要 + 图片列表重建可读正文，图片照常本地化。
- 一条命令可同时输出 `md` + `html`，默认落到知识库收件箱。

## 快速开始

要求：Python 3.10+（推荐 3.11）。Windows 用 PowerShell 封装 `spider.ps1`，Linux / macOS 用 bash 封装 `spider.sh`；两者都只负责定位解释器并把参数转发给 `spider.py`。

```powershell
cd D:\workSpace\cmd_utils\spider
pip install -r requirements.txt

# 看默认落点配置是否可用（知识库目录是否存在）
python .\spider.py --list-bases

# 抓一篇微信文章：默认输出 md 到 <知识库>/000-inbox
python .\spider.py "https://mp.weixin.qq.com/s/xxxxx"

# 同时输出 md + html，放到知识库的 001-Current_Projects/IoT 下
python .\spider.py "https://mp.weixin.qq.com/s/xxxxx" -F both -d A/IoT

# 输出到任意目录（不依赖知识库配置）
python .\spider.py "https://mp.weixin.qq.com/s/xxxxx" -o D:\temp\articles -F both
```

PowerShell 封装（参数原样转发给 Python，自动定位解释器）：

```powershell
# 直接运行脚本
.\spider.ps1 "https://mp.weixin.qq.com/s/xxxxx" -F both

# 点源后使用 spider 函数
. .\spider.ps1
spider "https://mp.weixin.qq.com/s/xxxxx" -F both -d B
```

Linux / macOS 同样支持（`spider.sh` 查找顺序：`SPIDER_PYTHON` → `.venv/bin/python` → `python3` → `python`）：

```bash
chmod +x ./spider.sh
./spider.sh "https://mp.weixin.qq.com/s/xxxxx" -F both -d A/IoT

# 或点源后使用 spider 函数
. ./spider.sh
spider "https://mp.weixin.qq.com/s/xxxxx" -F both
```

## 命令行参数

```text
spider URL [URL ...] [选项]
```

| 参数 | 说明 |
| --- | --- |
| `URL ...` | 文章地址，可一次传多个 |
| `-b, --batch FILE` | URL 列表文件，每行一个，支持 `#` 注释 |
| `-o, --out DIR` | 直接输出到指定目录（与 `-d` 二选一） |
| `-d, --dir SEG` | 知识库内子目录段，可重复；支持 `A/IoT` 写法与 A/B/C 别名 |
| `--base NAME` | 知识库根预设（见 `--list-bases`） |
| `-F, --format {md,html,both}` | 输出格式，默认 `md`；`both` 同时输出两种 |
| `-L, --image-links {relative,wikilink}` | Markdown 图片链接：相对路径或 Obsidian `![[images/x.png]]` |
| `-n, --skip-existing` | 目标文件都存在时跳过 |
| `--dry-run` | 只打印解析结果，不抓取 |
| `--open` | 有 html 输出时用默认浏览器打开 |
| `-q, --quiet` / `-v, --verbose` | 减少 / 增加日志 |
| `--config FILE` | 指定配置文件 |
| `--list-bases` / `--list-aliases` | 列出知识库预设 / 目录别名 |
| `--version` | 版本号 |

退出码：`0` 成功，`1` 有文章失败，`2` 配置或用法错误。

## 配置：spider.config.toml

知识库路径不再写死在代码里。配置文件查找顺序：

1. `--config FILE`
2. 环境变量 `SPIDER_CONFIG`
3. 仓库根目录的 `spider.config.toml`
4. `~/.config/spider/spider.config.toml`

```toml
default_base = "default"      # 默认知识库（[bases] 的键名）
default_inbox = "000-inbox"   # 不给 -d/-o 时落到这里

[bases]
default = "D:\\workSpace\\wen\\Repository\\obsidianDB"

[aliases]
A = "001-Current_Projects"
B = "002-raw_resource"
C = "003-wiki_schema"
```

其他可用环境变量：

- `SPIDER_VAULT`：临时覆盖 `[bases].default` 路径
- `SPIDER_BASE`：旧版环境变量名，作为 `SPIDER_VAULT` 的兼容回退；两者都设置时 `SPIDER_VAULT` 优先
- `SPIDER_PYTHON`：`spider.ps1` / `spider.sh` 使用的 Python 解释器路径

## 输出结构

```text
<目标目录>\
  <清洗后的标题>\
    <清洗后的标题>.md
    <清洗后的标题>.html      # -F html / -F both 时
    images\
      <md5>.<扩展名>          # 按图片魔数判定：.jpg / .png / .gif / .webp / .bmp
```

同名文章已存在时不会覆盖，而是新建 `<标题>_2/`、`<标题>_3/`……；只想跳过已抓取的文章用 `-n`。

Markdown frontmatter 字段：

```yaml
title: "..."
date: "2026-08-27 18:00"      # 微信从页面 JS 变量 ct/create_time 提取
source: "..."
platform: wechat | zhihu | web
account: "公众号名"            # 有则输出
author: "作者"                 # 有则输出
status: inbox
progress: 0
description: "..."
tags:
  - wechat
scraped_at: "..."
```

## 从旧参数迁移（已断代，旧参数会报错并提示）

| 旧用法 | 新用法 |
| --- | --- |
| `spider -u URL` / `--url URL` | `spider URL` |
| `spider -df A -df IoT` | `spider URL -d A/IoT` |
| `spider -f D:\out` | `spider URL -o D:\out` |
| `spider -o md`（旧语义=格式） | `spider URL -F md` |
| `spider --batch-file urls.txt` | `spider -b urls.txt` |
| `spider -o html` | `spider URL -F html` |
| `.\spider.ps1 -Help` | `.\spider.ps1 --help` |

## 常见问题

**HTML 打开后正文是空白？**
旧版本会把微信正文的 `visibility: hidden; opacity: 0` 原样保存；当前版本渲染前会自动清除。旧文件需要重新抓取。

**微信链接打开是验证/环境异常页？**
搜索页里的 `mp.weixin.qq.com/s?__biz=...` 链接常被 302 到验证页，抓不到正文。请使用在浏览器里能直接正常打开的 `/s/<id>` 文章链接。

**微信链接是「图片消息」或分享页？**
页面上没有 `rich_media_content` 正文容器，只有摘要和图片列表；当前版本会按「摘要 + 图片」重建可读正文，并把图片下载到 `images/`。若页面只显示"使用完整服务 / 请在微信中打开"，说明正文需要微信客户端，请换一个链接。

**知乎返回 403？**
知乎有独立反爬策略，当前版本不做 Cookie/登录态，可能抓取失败，请改用其他来源。

**提示"知识库目录不存在"？**
默认配置指向 `D:\workSpace\wen\Repository\obsidianDB`。换机器或换路径时修改 `spider.config.toml` 的 `[bases].default`，或改用 `-o`。

**PowerShell / bash 找不到 Python？**
在 `.venv` 中安装依赖，或设置 `SPIDER_PYTHON` 为解释器完整路径（PowerShell：`$env:SPIDER_PYTHON = "python.exe 的完整路径"`，bash：`export SPIDER_PYTHON=/usr/bin/python3`）。

**重复抓同一篇会覆盖旧文件吗？**
不会。同名文章目录已存在时自动新建 `<标题>_2/`、`<标题>_3/`；只想补缺可加 `-n`。

## 开发与测试

```powershell
# 单元测试（不需要网络，当前 103 个用例）
python -m unittest discover -s tests -v

# 只解析不抓取
python .\spider.py --dry-run "https://mp.weixin.qq.com/s/xxxxx" -d A/IoT -F both

# 真实抓取验证（产物在 tmp_out/，已 gitignore）
python .\spider.py "https://mp.weixin.qq.com/s/xxxxx" -o tmp_out\e2e -F both
```

## 提交与上传规范

提交信息使用 Conventional Commits 风格（`feat:` / `fix:` / `refactor:` / `docs:` / `test:` / `chore:`），破坏性变更在类型后加 `!` 并在正文注明 `BREAKING CHANGE:`；分支用 `feat/<主题>`、`fix/<主题>`。完整约定（含推送前检查项）见 [AGENT.md](AGENT.md) 的「提交与上传规范」一节。

## 目录结构

```text
spider.py                 入口（薄封装）
spider.ps1                Windows PowerShell 薄封装（只负责找 Python 并转发参数）
spider.sh                 Linux / macOS bash 薄封装（同上）
spider.config.toml        知识库路径与目录别名
spider_core/
  cli.py                  命令行参数（唯一解析源）
  config.py               配置加载与输出路径解析
  service.py              单篇文章保存流程（含重名去重）
  http.py                 共享 Session、请求与重试（失败抛 NetworkError）
  errors.py               SpiderError / NetworkError / ParseError / UnsupportedURLError
  models.py               ScrapedArticle
  scrapers/               平台识别与正文提取（wechat / zhihu / base）
  media.py                图片并发下载、魔数扩展名、链接改写
  html_cleaner.py         正文清洗（去隐藏样式、懒加载图、自定义标签）
  renderers.py            Markdown / 微信阅读模式 HTML 渲染
tests/                    unittest 测试
```
