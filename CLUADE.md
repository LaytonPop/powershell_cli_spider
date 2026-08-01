# CLUADE.md

本文件面向使用 Claude 类助手维护该仓库时的快速协作约定。内容尽量短、可执行、贴近当前代码，而不是通用模板。

## 先读什么

进入仓库后，优先阅读：

- `spider.py`
- `spider.sh` / `spider.ps1`（Linux 用前者，Windows 用后者）
- `spider_core/cli.py`
- `spider_core/service.py`
- `spider_core/config.py`
- `spider_core/scrapers/`
- `spider_core/errors.py`（失败模型）

这个项目的入口仍然简单，但 Python 真实逻辑现在主要在 `spider_core/` 里。

## 项目一句话

这是一个跨平台终端爬虫工具，用来把微信公众号和知乎文章抓取到本地知识库目录，并把图片一并保存到文章目录下。Windows 用 `spider.ps1`，Linux/macOS 用 `spider.sh`。

## 当前事实

- 默认知识库根目录是 `F:\workspace3\wen\Repository\obsidianDB`，可用 `SPIDER_BASE` 环境变量覆盖
- PowerShell 入口依赖固定 Python：`C:\Users\morganWen\.conda\envs\spider\python.exe`
- bash 入口不硬编码 Python：`SPIDER_PYTHON` 环境变量或 `python3`
- Python 入口 `spider.py` 现在是薄封装，核心逻辑在 `spider_core/`
- 当前支持输出：`html`、`md`
- 当前支持站点：`mp.weixin.qq.com`、`zhuanlan.zhihu.com`、`zhihu.com/question/<id>`（问题页取首答）
- 批量抓取已下沉到 Python CLI（`--batch-file`），包装层只转译参数
- 已有 `requirements.txt`（`requests`、`beautifulsoup4`、`html2text`）+ `pytest`（开发依赖）
- 爬取失败用异常区分：`NetworkError` / `ParseError` / `UnsupportedURLError`
- 日志用 `logging`（stderr，带时间戳）；`--dry-run` 解析结果走 stdout
- 去重：目标文件已存在时自动加 `_2`/`_3` 后缀，不覆盖旧文章

## 你在修改时要守住的行为

- 输入一个 URL 后，最终应在知识库中生成“文章目录 + 主文件 + images 子目录”
- Markdown 输出必须继续保留 frontmatter
- 图片链接必须继续改写为本地相对路径
- `-df` 目录参数必须继续支持别名展开：
  - `A -> 001-Current_Projects`
  - `B -> 002-raw_resource`
  - `C -> 003-wiki_schema`
- `-f` 现在表示直接完整输出路径，不再表示默认库下的目录段
- 包装层入口的“位置参数就是 URL”行为不要随意破坏
- 包装层入口的批量抓取功能不要随意破坏（现在委托给 Python `--batch-file`）
- `scrape()` 的契约是抛 `SpiderError` 子类，不要改回返回 `None`

## 高风险区域

- `ZhihuScraper.match()` 已收紧：专栏页与问题页各自走独立的 DOM 解析分支，但两个分支的选择器都可能随站点改版失效
- `spider.ps1` 中的 Python 路径和脚本路径是硬编码的，改动会直接影响用户日常调用（`spider.sh` 已改为自动定位）
- `spider.py` 只是入口，新增业务逻辑时不要再把实现堆回单文件
- 已有 `pytest` 测试（46 个用例），但全部是离线 mock；改 selector 或输出格式时仍需警惕真实站点回归
- 爬取失败现在抛异常（`NetworkError` / `ParseError` / `UnsupportedURLError`），调用方必须捕获 `SpiderError`，不要靠返回 `None` 判断

## 常见任务怎么做

### 新增站点

- 在 `spider_core/scrapers/` 中新增一个 `AbstractScraper` 子类
- 保持 `scrape()` 返回 `ScrapedArticle`
- 注册到 `spider_core/scrapers/__init__.py` 里的 `SCRAPERS`
- 如果该站点图片使用特殊属性，补 `spider_core/media.py`

### 调整输出目录逻辑

- 先检查 `spider_core/config.py` 中的 `BASES`
- 再检查 `ALIASES`
- 再检查 `resolve_default_output_dir()` 与 `normalize_output_path()`
- 最后检查 `spider_core/cli.py` 中 `-df` / `-f` 的互斥逻辑
- 若目录结构变化，务必同步更新 `spider.ps1` 的帮助文本和两个文档

### 调整命令行参数

- Python CLI 改动后，先检查 `spider_core/cli.py`
- 然后检查 `spider.py`、`spider.sh` 与 `spider.ps1` 是否还在正确传参
- 特别关注：
  - `-u/--url`
  - `-B/--batch-file`
  - `-df/--default-folder`
  - `-f/--full-path`
  - `-o/--format`
  - `--dry-run`

## 建议的最小验证

如果本次修改不涉及联网逻辑，至少做这些检查：

```powershell
python .\spider.py --help
python .\spider.py --list-bases
python .\spider.py --list-aliases
python .\spider.py --dry-run -df A -df Demo -o md
python .\spider.py --dry-run -f "F:\workspace3\wen\temp\articles" -o md
python -m pytest tests/ -q
```

Linux 上对应为：

```bash
SPIDER_BASE=/path/to/kb python3 spider.py --dry-run -df A -df Demo -o md
python3 -m pytest tests/ -q
```

如果改了 `spider.sh` / `spider.ps1`，再补一次：

```bash
bash spider.sh --help
```

```powershell
. .\spider.ps1
spider -Help
```

如果改了站点选择器或图片逻辑，最好再做一次真实 URL 抓取验证。

## 写代码时的偏好

- 优先保持当前脚本风格，先做小而准的修改
- 不要在没有说明的情况下把仓库改造成大型框架
- 若要引入配置文件、依赖管理或测试框架，可以做，但要解释迁移收益
- 若发现 `CLUADE.md` 是有意命名，就保持它；若用户后续希望对齐社区习惯，再改名为 `CLAUDE.md`

## 交付前检查

- 代码行为与文档一致
- `AGENT.md` 与本文件没有互相矛盾
- 若新增站点、参数或路径规则，两个文档都已同步
