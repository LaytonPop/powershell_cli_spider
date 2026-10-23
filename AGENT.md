# AGENT.md

本文件面向后续维护这个仓库的 AI Agent / 协作者：说明当前真实架构、必须守住的行为、验证方式。修改前先读本文件和 `README.md`。

注意：本工具仅用于个人学习与资料归档，必须符合法律要求、尊重目标网站服务条款，不能用于侵犯他人权益的用途。

## 项目一句话

跨平台终端文章抓取工具（Windows PowerShell / Linux、macOS bash）：把微信公众号 / 知乎文章正文和图片抓到本地知识库，输出 Markdown 或自包含 HTML（微信阅读模式）。

## 技术栈

- Python 3.10+（实测 3.11）
- `requests`（HTTP）、`beautifulsoup4`（解析/清洗）、`html2text`（HTML→Markdown）
- HTTP 使用共享 `requests.Session`；图片用 `ThreadPoolExecutor` 并发下载（默认 8 线程），扩展名按文件头魔数判定
- 测试用标准库 `unittest`，不引入第三方测试框架
- 不依赖浏览器 / playwright；HTML 渲染完全在 Python 内完成

## 模块职责

| 路径 | 职责 |
| --- | --- |
| `spider.py` | 入口，只调用 `spider_core.cli.main` |
| `spider.ps1` | Windows PowerShell 薄封装：定位 Python（`SPIDER_PYTHON` → `.venv` → conda 环境 → PATH）并把参数原样转发，**不做参数解析** |
| `spider.sh` | Linux / macOS bash 薄封装：定位 Python（`SPIDER_PYTHON` → `.venv/bin/python` → `python3` → `python`）并原样转发参数，**不做参数解析** |
| `spider.config.toml` | 知识库根目录 `[bases]`、目录别名 `[aliases]`、默认收件箱 |
| `spider_core/cli.py` | 唯一的命令行解析源；参数定义、dry-run、日志与退出码 |
| `spider_core/config.py` | 配置查找与加载、`SpiderConfig`、目录段拆分、别名展开、输出路径解析 |
| `spider_core/service.py` | 单篇文章保存流程（含 `_unique_article_dir` 重名去重），返回 `SaveResult` |
| `spider_core/http.py` | 共享 `requests.Session`、请求与重试（3 次、指数退避、15s 超时），失败抛 `NetworkError` |
| `spider_core/errors.py` | 错误层级：`SpiderError` → `NetworkError` / `ParseError` / `UnsupportedURLError` |
| `spider_core/models.py` | `ScrapedArticle` 数据结构 |
| `spider_core/scrapers/` | 平台识别与正文/元数据提取（`wechat.py`、`zhihu.py`、`base.py`）；抓取失败抛 `SpiderError` 子类 |
| `spider_core/media.py` | 图片并发下载、魔数扩展名、`images/<md5>.<ext>` 命名、正文链接改写 |
| `spider_core/html_cleaner.py` | 正文清洗：去掉 `visibility`/`opacity`、根节点 `display:none`、懒加载图规范化、微信自定义标签占位 |
| `spider_core/renderers.py` | Markdown 生成（frontmatter + html2text）与微信阅读模式 HTML 模板 |
| `tests/` | 单元测试（不联网） |

## 数据流

1. `cli.main` 解析参数、加载配置、解析输出目录
2. `service.save_article` → `scrape_article(url)` → `find_scraper(url)` + `scraper.scrape(url)` 得到 `ScrapedArticle`；网络/解析失败以 `SpiderError` 子类抛出，由 `save_article` 收进 `SaveResult.error`
3. 建文章目录 `<输出目录>/<sanitize_filename(title)>/`；同名已存在时用 `_2`、`_3` 后缀，不覆盖旧文章
4. `media.download_and_rewrite_images` 并发下载图片并改写为 `images/<md5>.<ext>`
5. `renderers.render_documents` 生成所需格式：
   - HTML：`html_cleaner.clean_article_html` 清洗后套阅读模式模板
   - Markdown：`html2text` 转换 + YAML frontmatter
6. 写入文件，`cli` 输出日志并按失败数决定退出码

## 必须守住的不变量

- Markdown 必须保留 YAML frontmatter（字段见 `README.md`；`date` 仅在提取到发布时间时输出）。
- 正文图片必须本地化到 `images/`，Markdown 默认相对路径，`-L wikilink` 用 `![[images/x]]`。
- 同名文章目录已存在时必须新建 `<标题>_2/`、`<标题>_3/`，不得覆盖已有文章；`-n/--skip-existing` 只跳过不重抓。
- 抓取失败必须抛 `SpiderError` 子类（`NetworkError` / `ParseError` / `UnsupportedURLError`），由 CLI 捕获后计入失败数，不要吞掉异常返回空结果。
- HTML 输出必须清除会让正文不可见的样式（`visibility`、`opacity`、正文根节点的 `display:none`），不得回归成"打开空白"。
- Python CLI 是唯一参数解析源；`spider.ps1` / `spider.sh` 只能转发参数，不要重新在里面写一套解析。
- 默认输出格式为 `md`，默认落点为 `default_inbox`（默认 `000-inbox`）。
- `-o/--out` 是直接输出目录，`-d/--dir` 是知识库内目录段，两者互斥。
- 目录别名 `A/B/C` 展开为 `001-Current_Projects / 002-raw_resource / 003-wiki_schema`；未知别名原样保留。
- 旧参数（`-u/--url`、`-df`、`-f`、`--batch-file`）已移除，保留解析入口只为输出迁移提示；不要静默重新兼容。
- Cookie 只能来自 `--cookie` / `--cookie-file` / `SPIDER_COOKIE`，不得写死在代码里；从 CLI 一路透传到 `retry_request(headers={"Cookie": ...})`，日志只显示长度、不回显内容。

## 命令行（当前事实）

```text
spider URL [URL ...] [-b FILE] [-o DIR | -d SEG ...] [--base NAME]
       [-F md|html|both] [-L relative|wikilink] [-n] [--dry-run] [--open]
       [--cookie HEADER | --cookie-file FILE]
       [-q|-v] [--config FILE] [--list-bases] [--list-aliases] [--version]
```

示例：

```powershell
python .\spider.py "https://mp.weixin.qq.com/s/xxx" -F both -d A/IoT
python .\spider.py "url1" "url2" -o D:\temp\articles
python .\spider.py -b urls.txt -d B -F md -n
python .\spider.py --dry-run "https://mp.weixin.qq.com/s/xxx"
python .\spider.py "https://zhuanlan.zhihu.com/p/xxx" -o D:\note --cookie "z_c0=...; d_c0=..."
```

## 平台与选择器

- 微信：URL 含 `mp.weixin.qq.com`；标题 `h1.rich_media_title` / `og:title` / `var msg_title`；正文 `div.rich_media_content` 或 `#js_content`；发布时间优先页面文本，否则从 `var ct` / `var create_time` 时间戳格式化；公众号名优先 `#js_name`，否则 `nickname` JS 变量 / `nick_name` 字段 / `og:article:author`。图片消息 / 分享页没有正文容器（含 `picture_page_info_list`、`share_content_page` 标记）时，用 `cgiDataNew` 里的 `content_noencode` 摘要 + `picture_page_info_list[].cdn_url` 重建正文（`wechat-image-share`）。
- 知乎：`zhuanlan.zhihu.com`（专栏文章：标题 `h1.Post-Title`，正文 `div.Post-RichText`，时间 `.ContentItem-time` 或 `meta[itemprop=datePublished]`）或 `www.zhihu.com/question`（问题页：标题 `h1.QuestionHeader-title`，正文取首个 `div.RichContent-inner` / `div.AnswerCard` / `div.RichContent`，时间 `meta[itemprop=dateModified]`，作者 `.AuthorInfo-name`）。
- 其他 URL 会被拒绝（"不支持的 URL 类型"）。

## 配置系统

查找顺序：`--config` → `SPIDER_CONFIG` → 仓库根 `spider.config.toml` → `~/.config/spider/spider.config.toml`。
`SPIDER_VAULT` 可覆盖 `[bases].default`；旧版 `SPIDER_BASE` 作为兼容回退（两者都设置时 `SPIDER_VAULT` 优先）。
知识库目录不存在时，非 dry-run 会报错退出（提示改配置或改用 `-o`）。

## 验证方式

```powershell
# 1. 单元测试（无网络，当前 113 个用例）
python -m unittest discover -s tests -v

# 2. 参数解析冒烟（不抓取）
python .\spider.py --help
python .\spider.py --version
python .\spider.py --list-bases
python .\spider.py --list-aliases
python .\spider.py --dry-run "https://mp.weixin.qq.com/s/xxx" -d A/IoT -F both

# 3. 包装脚本
.\spider.ps1 --version
. .\spider.ps1; spider --version

# Linux / macOS（WSL、Git Bash 均可）
./spider.sh --version
. ./spider.sh; spider --version

# 4. 真实抓取 E2E（产物在 tmp_out/，已 gitignore）
python .\spider.py "https://mp.weixin.qq.com/s/SSU_GOBTHxiGQGPAF0xSHg" -o tmp_out\e2e -F both
# 校验：产物 html 中不应出现 "visibility"/"opacity"，应包含 3 张以上本地图片
```

改站点选择器或渲染逻辑时，必须补做真实抓取；必要时用 Chrome headless 截图肉眼确认 HTML 可读：

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new --disable-gpu `
  --hide-scrollbars --window-size=1100,1700 --screenshot="$PWD\tmp_out\shot.png" `
  "file:///.../<文章目录>/<标题>.html"
```

## 常见任务

- **新增站点**：在 `spider_core/scrapers/` 新建 `AbstractScraper` 子类并注册到 `__init__.py` 的 `SCRAPERS`；特殊图片属性补到 `media.LAZY_IMAGE_ATTRIBUTES`；补元数据提取与测试。
- **调整输出目录规则**：只改 `config.py`（`SpiderConfig` / `split_dir_segments` / `resolve_alias`），CLI 不重复实现。
- **新增输出格式**：在 `renderers.FORMAT_EXTENSIONS`、`render_documents`、`cli.FORMAT_TARGETS` 三处同步，并补测试。
- **HTML 又变空白**：先检查保存产物中是否残留 `visibility`/`opacity`/根节点 `display:none`，再看 `html_cleaner.clean_style` 与 `_is_content_root` 的判定是否覆盖新的容器写法。
- **发布时间缺失**：微信先看原文页 `var ct` / `var create_time` 是否改名；知乎看 `.ContentItem-time` 是否仍存在。
- **知乎 403**：确认 `--cookie` / `SPIDER_COOKIE` 已传入（日志会显示“Cookie: 已加载 (N 字符)”）；Cookie 过期需重新从浏览器复制；不要用 UA 伪装等方式绕过。

## 已知限制

- 知乎可能返回 403（反爬），需要浏览器登录态 Cookie（`--cookie` / `--cookie-file` / `SPIDER_COOKIE`）；Cookie 过期或缺失时仍会失败。问题页只抓首个回答。
- 微信音频、视频、小程序、公众号名片在离线 HTML 中只显示占位文案。
- 图片并发下载（默认 8 线程）无进度条；失败图片保留原始远程链接并打 warning。
- 微信 `author` 常为空（页面本身未提供）。
- 搜索结果里的 `mp.weixin.qq.com/s?__biz=...` 链接常跳验证页，只能用可直接打开的文章链接。

## 提交前检查

- `python -m unittest discover -s tests -v` 全绿。
- `--dry-run` 与 `--list-bases` 的行为和 README 一致。
- 若改了 CLI 参数、输出结构、默认路径，同步更新 `README.md` 与本文件、`CLUADE.md`。
- 不把 `tmp_out/`、抓取产物、真实知识库路径之外的临时文件提交进仓库。

## 提交与上传规范

从 v1.0.0 起，本仓库的提交信息与分支命名统一按下面约定执行（此前历史提交不追溯）：

**提交信息：Conventional Commits 风格**

```text
<type>(<scope>): <中文摘要>

<可选的正文，每行一个要点>
```

- `type`：`feat` 新功能、`fix` 修复、`refactor` 重构、`test` 测试、`docs` 文档、`chore` 杂项、`perf` 性能、`build` 构建/依赖。
- `scope` 可省略，常用：`cli`、`config`、`renderers`、`scrapers`、`media`、`ps1`、`tests`、`docs`。
- 摘要用中文、尽量不超过 50 字、结尾不加句号；正文说明动机、影响与验证方式。
- 破坏性变更：`type` 后加 `!`（如 `refactor(cli)!: ...`），并在正文写一行 `BREAKING CHANGE: <不兼容点 + 迁移方式>`。

**分支命名**

- `feat/<短横线主题>`、`fix/<短横线主题>`、`docs/<主题>`、`chore/<主题>`。
- `main` 只接受通过测试的合并；个人小改动可直接在 `main` 提交。

**提交粒度**

- 一个提交只做一件事：功能/修复与对应测试可同提交，文档、配置、格式调整单独提交。

**上传（push）步骤**

1. `git status`：确认没有抓取产物、临时文件、本机路径噪音（`tmp_out/`、`.alma-snapshots` 已忽略）。
2. `python -m unittest discover -s tests` 全绿。
3. `git pull --rebase origin main`。
4. `git push origin main`（提交信息即上传命名依据，推送后 `git log -1 --oneline` 应与远端一致）。

**版本号与发布标签**

- `spider_core/cli.py` 的 `VERSION` 是唯一版本源；不兼容的参数或输出结构变更升主版本，功能新增升次版本。
- 每次发布在通过测试的 `main` 提交上打注释标签 `v<major>.<minor>.<patch>`（如 `v1.0.0`），推送时带上标签：`git push origin main --follow-tags`。

