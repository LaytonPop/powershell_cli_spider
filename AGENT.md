# AGENT.md

本文件面向后续维护这个仓库的 AI Agent / 协作者，目标是让人快速理解这个工具当前的真实状态，并在修改时保持行为一致。注意：必须符合法律要求，不能侵犯他人的权益，这个是要全局注意的。

## 项目目标

这是一个面向终端使用的文章爬虫工具，用来把网页文章抓取到本地知识库目录中，当前重点是：

- 从指定文章 URL 抓取正文
- 下载正文中的图片到本地
- 生成适合归档的 `html` 或 `md` 文件
- 按知识库目录结构存放到固定 base path 下

当前仓库的入口仍然很精简，但 Python 核心已经拆成模块：

- `spider.py`：Python 薄入口，只负责调用 CLI
- `spider.ps1`：PowerShell 包装函数，负责更顺手的终端调用和批量抓取
- `spider_core/`：Python 核心模块，负责配置、抓取器、图片处理、渲染、保存流程、CLI

## 当前运行假设

- 支持 Windows + PowerShell（`spider.ps1`）与 Linux/macOS + bash/zsh（`spider.sh`）
- `spider.ps1` 假定存在固定的 conda Python：
  - `C:\Users\morganWen\.conda\envs\spider\python.exe`
- `spider.ps1` 假定脚本入口固定放在：
  - `F:\workspace3\cmd_utils\spider\spider.py`
- `spider.sh` 不硬编码 Python 路径，按顺序使用：
  - 环境变量 `SPIDER_PYTHON`（如指定）
  - `python3`（PATH 中查找）
- `spider.sh` 的脚本入口自动定位到其同级目录下的 `spider.py`
- `SPIDER_BASE` 环境变量可覆盖默认知识库根目录（优先级高于 `config.py` 的 `BASES["default"]`）
- `spider.py` 使用了 Python 3.10+ 语法：
  - `list[str]`
  - `str | None`
- 当前已有 `requirements.txt`，代码依赖这些第三方包：
  - `requests`
  - `beautifulsoup4`
  - `html2text`
- 开发依赖：`pytest`（测试套件在 `tests/`，46 个用例，全部离线可跑）

如果要做环境整理，优先补齐依赖清单与路径配置化，而不是继续扩大硬编码路径。

## 模块结构

当前推荐从下面这些文件建立上下文：

- `spider.py`
- `spider.ps1`
- `spider_core/cli.py`
- `spider_core/service.py`
- `spider_core/config.py`
- `spider_core/scrapers/`

模块职责如下：

- `spider_core/config.py`
  - 基础配置
  - `BASES`
  - `ALIASES`
  - 输出目录解析
- `spider_core/http.py`
  - 页面抓取重试逻辑
- `spider_core/models.py`
  - `ScrapedArticle` 数据结构
- `spider_core/scrapers/`
  - 平台识别与正文提取
- `spider_core/media.py`
  - 图片下载与正文图片链接改写
- `spider_core/renderers.py`
  - HTML / Markdown 生成
- `spider_core/service.py`
  - 文章保存主流程
- `spider_core/cli.py`
  - CLI 参数与命令行行为

这套拆分的目标是：

- 保留现有 CLI 和 PowerShell 工作流
- 让核心逻辑可以被未来的 MCP、桌面 agent、RAG 管线复用
- 让新增站点和调整输出结构时只改对应模块

## 当前支持的平台

- 微信公众号：通过 `mp.weixin.qq.com` 匹配
- 知乎文章 / 专栏页：通过 `zhuanlan.zhihu.com` 匹配
- 知乎问题页：通过 `zhihu.com/question/<id>` 匹配，提取问题标题 + 首个高赞回答

注意：

- 知乎专栏页抓取依赖 `h1.Post-Title` 和 `div.Post-RichText`
- 知乎问题页抓取依赖 `h1.QuestionHeader-title` 和 `div.RichContent-inner`（回退 `AnswerCard` / `RichContent`）
- 若用户反馈“知乎页面抓不到内容”，优先检查 DOM 选择器，而不是怀疑保存逻辑

## 输出路径约定

Python 主程序现在支持两种输出模式：

- 默认知识库模式：使用 `-df`
- 直接路径模式：使用 `-f`

默认知识库模式通过 `BASES` 和 `ALIASES` 决定输出目录。

当前 `BASES` 只有一个预设：

- `default` -> `F:\workspace3\wen\Repository\obsidianDB`

当前 `ALIASES`：

- `A` -> `001-Current_Projects`
- `B` -> `002-raw_resource`
- `C` -> `003-wiki_schema`

规则：

- `-df A` 会解析成 `001-Current_Projects`
- `-df B` 会解析成 `002-raw_resource`
- `-df C` 会解析成 `003-wiki_schema`
- `-df A -df mathcs` 会输出到 `default\001-Current_Projects\mathcs`

直接路径模式下：

- `-f` 接收完整路径
- 不做 alias 展开
- 不拼接默认知识库根目录

最终文章输出结构如下：

```text
<base>\<folder...>\<sanitized_title>\
  <sanitized_title>.html | <sanitized_title>.md
  images\
    <md5>.<ext>
```

其中：

- 文章目录名由标题清洗后生成
- 非法文件名字符会被移除
- 空白会被替换成 `_`
- 文件名最长保留 100 个字符

## 主流程

当前 Python 主流程如下：

1. 解析 CLI 参数（支持单条与 `--batch-file` 批量）
2. 根据 URL 在 `spider_core.scrapers` 中找到匹配的平台爬虫
3. 请求文章页面，失败时最多重试 3 次，并采用指数退避；全部失败抛 `NetworkError`
4. 根据 `-df` 或 `-f` 解析输出目录
5. 为该文章创建独立目录（目标文件已存在时自动加 `_2`/`_3` 后缀防覆盖）
6. 提取标题、正文 HTML、发布时间、来源 URL；提取失败抛 `ParseError`
7. 下载正文中的图片到 `images/`（`ThreadPoolExecutor` 并发下载，复用共享 Session）
8. 将正文内图片链接改写成相对本地路径
9. 生成 HTML 或 Markdown 文件
10. 将结果写入目标目录

失败模型（`spider_core/errors.py`）：

- `NetworkError`：网络请求失败（重试后仍失败）
- `ParseError`：页面拿到了但解析不到内容
- `UnsupportedURLError`：没有爬虫匹配该 URL
- `scrape()` 不再返回 `None`，调用方（含批量模式）按异常类型区分失败原因

## 输出格式约定

### HTML 输出

- 使用 `build_html_doc()`
- 外层会包一层带简单样式的完整 HTML 页面
- 页面中包含：
  - 标题
  - 发布时间
  - 来源链接
  - 抓取时间
  - 正文 HTML

### Markdown 输出

- 使用 `build_markdown_doc()`
- 先用 `html2text` 将 HTML 转成 Markdown
- 文件头包含 YAML frontmatter：
  - `title`
  - `date`（若有）
  - `source`
  - `scraped_at`
- 正文前会追加一级标题 `# {title}`

## 图片处理规则

图片下载由 `spider_core/media.py` 中的 `download_and_rewrite_images()` 完成，当前行为很重要：

- 会自动创建 `images/` 目录
- 会处理微信公众号常见懒加载属性：
  - `data-wxsrc`
  - `data-src`
  - `data-original-src`
- `data:` 内联图片会被跳过
- 相对路径和 `//` 协议相对路径会被转成绝对 URL
- 图片文件名使用图片 URL 的 MD5 值，避免重名
- 图片保存后，正文中的 `src` 会被重写为 `images/<filename>`

当前限制：

- 图片下载复用共享 `requests.Session`（`http.get_session()`），并发线程数为 8（`DEFAULT_MAX_WORKERS`）
- 图片扩展名判定顺序：魔数嗅探 > URL 后缀 > Content-Type > `.jpg` 回退
- 知乎/微信对数据中心 IP 或非浏览器 UA 可能返回 403（重试后报 `NetworkError`），属站点反爬限制，不是脚本 bug

## 包装层

`spider.ps1`（Windows/PowerShell）与 `spider.sh`（Linux/macOS，bash/zsh）是两个等价入口，都可以：

- 单个 URL 抓取
- 通过 `-BatchFile` / `-B` 按行读取 URL 进行批量抓取（批量循环已下沉到 Python CLI 的 `--batch-file`，两个包装层都只是转译参数）

`spider.ps1` / `spider.sh` 额外做了这些事情：

- 把位置参数直接当作 URL
- 将 `-Format` / `-o` 映射为 Python 的 `-o`
- 将多个 `-DefaultFolder` / `-df` 映射为多个 `-df`
- 将 `-FullPath` / `-f` 映射为 Python 的 `-f`
- `spider.ps1` 对批处理文件逐行调用 Python 脚本（旧行为）

注意：

- Python 主程序自带 `--batch-file` 批量模式（`#` 开头为注释行，兼容 CRLF），退出码：全部成功 0，有失败 1
- `-df` 与 `-f` 是互斥的，不能同时使用
- 若修改 Python CLI 参数名，必须同步更新 `spider.ps1` 与 `spider.sh`

## 常用命令

### 直接调用 Python

```powershell
python .\spider.py -u "https://mp.weixin.qq.com/s/xxx" -df A -df IoT -o md
```

```powershell
python .\spider.py --dry-run -df A -df IoT -o md
```

```powershell
python .\spider.py -u "https://zhuanlan.zhihu.com/p/xxxx" -f "F:\workspace3\wen\temp\articles" -o html
```

```powershell
python .\spider.py --list-bases
python .\spider.py --list-aliases
```

### Linux / macOS（bash / zsh）

先设置知识库根目录（不设置则用 `config.py` 的默认值）：

```bash
export SPIDER_BASE="/home/you/Repository/obsidianDB"
./spider.sh -u "https://mp.weixin.qq.com/s/xxx" -df A -df IoT -o md
./spider.sh https://zhuanlan.zhihu.com/p/xxxx -f /home/you/articles -o html
./spider.sh -B urls.txt -df B -o md --dry-run
```

也可以 source 后直接用函数：

```bash
source ./spider.sh
spider "https://mp.weixin.qq.com/s/xxx" -o md -df A
```

批量模式（Python CLI 原生支持）：

```bash
python3 spider.py --batch-file urls.txt -df B -o md
```

### PowerShell 包装函数

先把函数载入当前 shell：

```powershell
. .\spider.ps1
```

然后执行：

```powershell
spider "https://mp.weixin.qq.com/s/xxx" -o md -df A -df IoT
```

```powershell
spider -u "https://zhuanlan.zhihu.com/p/xxxx" -o html -f "F:\workspace3\wen\temp\articles"
```

```powershell
spider -BatchFile "F:\workspace3\wen\idea\urls.txt" -o html -df B
```

## 新增站点时的约定

新增平台时，保持最小改动路径：

1. 在 `spider_core/scrapers/` 下新增一个文件，或在合适文件中新增一个抓取器类
2. 继承 `AbstractScraper`
3. 实现：
   - `match(url)`
   - `scrape(url)`
4. `scrape()` 返回统一结构：
   - `ScrapedArticle`
   - 或与其字段完全一致的数据
5. 将实例加入 `spider_core/scrapers/__init__.py` 中的 `SCRAPERS`
6. 如该站图片使用特殊懒加载属性，在 `spider_core/media.py` 中补充
7. 若该站点需要特殊清洗逻辑，优先收敛到该站抓取器内部，不要把站点分支散落到 CLI 或保存层
8. 同步更新本文件和 `CLUADE.md`

## 如何新增站点

推荐步骤：

1. 先确认是否真的属于“文章页”抓取，而不是列表页、搜索页或登录态页面
2. 在 `spider_core/scrapers/` 新建抓取器，例如 `new_site.py`
3. 在该文件中实现：
   - URL 匹配
   - 页面请求后的 DOM 解析
   - 标题提取
   - 正文提取
   - 发布时间提取
4. 返回 `ScrapedArticle`
5. 在 `spider_core/scrapers/__init__.py` 注册实例
6. 如果图片链接不是标准 `src`，补 `spider_core/media.py`
7. 跑最小验证：
   - `python .\spider.py --help`
   - `python .\spider.py --dry-run -df A -o md`
   - `python .\spider.py --dry-run -f "F:\workspace3\wen\temp\articles" -o md`
   - 真实 URL 抓取验证
8. 更新 `AGENT.md` 与 `CLUADE.md` 中的支持站点说明

新增站点时的注意事项：

- 不要为了某一个站点去改全局输出结构
- 不要随意改 CLI 参数名
- 优先把站点差异封装在 scraper 内部
- 如果站点依赖登录、cookie 或 JS 渲染，要在文档里明确说明
- 若新站点引入额外依赖，必须同步更新依赖说明

## 如何调整输出目录结构

目录结构调整时，优先检查这些位置：

1. `spider_core/config.py`
   - `BASES`
   - `ALIASES`
   - `resolve_output_dir()`
   - `resolve_default_output_dir()`
   - `normalize_output_path()`
2. `spider_core/renderers.py`
   - 文件名清洗逻辑
3. `spider_core/service.py`
   - 文章目录
   - `images/` 子目录
   - 主文件扩展名
4. `spider.ps1`
   - 帮助文本中的示例和别名说明
5. `AGENT.md` / `CLUADE.md`
   - 输出路径约定
   - 常用命令

调整时的原则：

- 优先保持“文章独立目录 + 主文件 + images 子目录”不变
- 若必须变更目录层级，要明确旧路径是否兼容
- 不要只改 Python，不改 PowerShell 帮助文本
- 不要只改代码，不改文档

## 维护注意事项

- 不要默默改动 `BASES`、`ALIASES`、Python 路径或脚本路径；这些都是用户工作流的一部分
- 如果要把硬编码路径改成配置文件，需要同时处理 Python 与 PowerShell/bash 两层入口
- `spider.py` 现在是薄入口，业务逻辑优先放在 `spider_core/`，不要重新堆回单文件
- DOM 选择器很脆弱，站点一改版就可能失效
- 已有 `tests/` 测试套件（`pytest`，46 个用例，全部离线可跑），改动后至少运行：`python -m pytest tests/ -q`
- 每次改动后至少做一次：`--dry-run`、`--list-bases`、本地单条抓取验证
- 去重机制：目标文件已存在时自动加 `_2`/`_3` 后缀，不会静默覆盖旧文章
- 日志分级：`logging` 输出到 stderr（INFO/ERROR），带时间戳；`--dry-run` 的解析结果走 stdout
- `sanitize_filename()` 空标题回退已改为 `article_` + MD5 前 8 位，并拦截 `.`/`..`/隐藏文件名
- 爬取失败通过异常区分：`NetworkError`（网络）、`ParseError`（解析）、`UnsupportedURLError`（不支持）

## 已知待优化项

按优先级排列，供后续迭代参考。

### 可靠性（高优先级）

- **知乎/微信反爬**：数据中心 IP 容易 403，可支持自定义 cookie / Referer（`HEADERS` 目前只有 UA）
- **真实站点回归样例**：`tests/` 目前用离线 mock HTML，建议沉淀少量真实抓取结果作为 golden 样例

### 效率（中优先级）

- **知乎问题页多回答**：目前只取首个高赞回答，可支持选择回答或合并全部回答
- **PowerShell 参数解析简化**：`ConvertTo-SpiderArguments` 手写 ~100 行 switch，可用 `Param()` 块精简

### 工程化（低优先级）

- **配置化**：`BASES` 目前仅支持 `SPIDER_BASE` 环境变量覆盖，可迁移到 `~/.config/spider.toml`
- **Markdown 后处理**：`html2text` 输出偶有多余空行或断裂表格，可加一层清理
- **批量并发**：`process_batch` 目前串行处理 URL，可按需并行（注意站点限流风险）

## 建议的后续演进方向

- 为 `spider_core` 提供稳定的程序化 API，供 MCP 或桌面 agent 直接调用
- 把硬编码路径迁移到配置文件或环境变量（已支持 `SPIDER_BASE`，可进一步做配置文件）
- 为各平台提取逻辑补真实站点回归样例
- 为批量抓取增加并发与断点续抓
- 为知乎问题页补充多回答选择逻辑

## 文档同步要求

以下改动发生时，必须同步更新 `AGENT.md` 与 `CLUADE.md`：

- 支持的新站点发生变化
- CLI 参数发生变化
- base path / alias 规则发生变化
- 输出目录结构发生变化
- `-df` / `-f` 模式语义发生变化
- PowerShell 包装层调用方式发生变化
- Python 模块结构发生变化
- Python 依赖或环境假设发生变化
