# AGENT.md

本文件面向后续维护这个仓库的 AI Agent / 协作者，目标是让人快速理解这个工具当前的真实状态，并在修改时保持行为一致。

## 项目目标

这是一个面向终端使用的文章爬虫工具，用来把网页文章抓取到本地知识库目录中，当前重点是：

- 从指定文章 URL 抓取正文
- 下载正文中的图片到本地
- 生成适合归档的 `html` 或 `md` 文件
- 按知识库目录结构存放到固定 base path 下

当前仓库非常精简，核心只有两个入口文件：

- `spider.py`：Python 主程序，负责 CLI、站点识别、正文提取、图片下载、文档输出
- `spider.ps1`：PowerShell 包装函数，负责更顺手的终端调用和批量抓取

## 当前运行假设

- 运行环境是 Windows + PowerShell
- `spider.ps1` 假定存在固定的 conda Python：
  - `C:\Users\morganWen\.conda\envs\spider\python.exe`
- `spider.ps1` 假定脚本固定放在：
  - `F:\workspace3\cmd_utils\spider\spider.py`
- `spider.py` 使用了 Python 3.10+ 语法：
  - `list[str]`
  - `str | None`
- 当前未提供 `requirements.txt` 或锁文件，代码直接依赖这些第三方包：
  - `requests`
  - `beautifulsoup4`
  - `html2text`

如果要做环境整理，优先补齐依赖清单与路径配置化，而不是继续扩大硬编码路径。

## 当前支持的平台

- 微信公众号：通过 `mp.weixin.qq.com` 匹配
- 知乎文章 / 问题页：通过 `zhuanlan.zhihu.com` 或 `www.zhihu.com/question` 匹配

注意：

- 知乎抓取逻辑当前依赖 `h1.Post-Title` 和 `div.Post-RichText`
- 这更像是知乎专栏页的 DOM 结构
- 虽然 `match()` 允许问题页 URL，但问题页未必总能被当前解析逻辑正确提取

如果用户反馈“知乎问题页抓不到内容”，优先检查 DOM 选择器，而不是怀疑保存逻辑。

## 输出路径约定

Python 主程序通过 `BASES` 和 `ALIASES` 决定输出目录。

当前 `BASES` 只有一个预设：

- `default` -> `F:\workspace3\wen\Repository\obsidianDB`

当前 `ALIASES`：

- `A` -> `001-Current_Projects`
- `B` -> `002-raw_resource`
- `C` -> `003-wiki_schema`

规则：

- `-f A` 会解析成 `001-Current_Projects`
- `-f B` 会解析成 `002-raw_resource`
- `-f C` 会解析成 `003-wiki_schema`

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

`spider.py` 当前工作流如下：

1. 解析 CLI 参数
2. 根据 URL 在 `SCRAPERS` 中找到匹配的平台爬虫
3. 请求文章页面，失败时最多重试 3 次，并采用指数退避
4. 提取标题、正文 HTML、发布时间、来源 URL
5. 为该文章创建独立目录
6. 下载正文中的图片到 `images/`
7. 将正文内图片链接改写成相对本地路径
8. 生成 HTML 或 Markdown 文件
9. 将结果写入知识库目录

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

图片下载由 `_download_and_rewrite()` 完成，当前行为很重要：

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

- 文章页请求使用了重试逻辑
- 图片请求没有复用 `retry_request()`，失败会直接跳过
- 只根据 URL 后缀或 `Content-Type` 推断少量常见图片格式

## PowerShell 包装层

`spider.ps1` 定义了一个 `spider` 函数，不是独立 exe。

它提供了两类调用方式：

- 单个 URL 抓取
- 通过 `-BatchFile` 按行读取 URL 进行批量抓取

它额外做了这些事情：

- 把位置参数直接当作 URL
- 将 `-Format` 映射为 Python 的 `-o`
- 将多个 `-Folder` 映射为多个 `-f`
- 对批处理文件逐行调用 Python 脚本

注意：

- Python 主程序本身没有批处理模式
- 批处理能力只存在于 `spider.ps1`
- 若修改 Python CLI 参数名，必须同步更新 `spider.ps1`

## 常用命令

### 直接调用 Python

```powershell
python .\spider.py default -u "https://mp.weixin.qq.com/s/xxx" -f A-Current_Projects -f IoT -o md
```

```powershell
python .\spider.py --dry-run -f A-Current_Projects -f IoT -o md
```

```powershell
python .\spider.py --list-bases
python .\spider.py --list-aliases
```

### PowerShell 包装函数

先把函数载入当前 shell：

```powershell
. .\spider.ps1
```

然后执行：

```powershell
spider "https://mp.weixin.qq.com/s/xxx" -Format md -Folder A-Current_Projects -Folder IoT
```

```powershell
spider -BatchFile "F:\workspace3\wen\idea\urls.txt" -Format html -Folder B-Reading
```

## 新增站点时的约定

新增平台时，保持最小改动路径：

1. 继承 `AbstractScraper`
2. 实现：
   - `match(url)`
   - `scrape(url)`
3. `scrape()` 返回统一结构：
   - `title`
   - `html_content`
   - `publish_time`
   - `source_url`
4. 将实例加入 `SCRAPERS`
5. 如该站图片使用特殊懒加载属性，在 `_download_and_rewrite()` 中补充
6. 同步更新本文件和 `CLUADE.md`

## 维护注意事项

- 不要默默改动 `BASES`、`ALIASES`、Python 路径或脚本路径；这些都是用户工作流的一部分
- 如果要把硬编码路径改成配置文件，需要同时处理 Python 与 PowerShell 两层入口
- DOM 选择器很脆弱，站点一改版就可能失效
- 当前没有自动测试，任何改动后至少要做一次：
  - `--dry-run`
  - `--list-bases`
  - 本地单条抓取验证
- 当前没有去重机制，同一篇文章重复抓取会复用同目录并覆盖同名主文件
- 当前没有日志分级，报错主要依赖 stderr 输出

## 建议的后续演进方向

- 补 `requirements.txt` 或 `pyproject.toml`
- 把硬编码路径迁移到配置文件或环境变量
- 为各平台提取逻辑补最小回归样例
- 为批量抓取增加失败汇总
- 为知乎问题页补单独解析逻辑
- 为图片下载复用重试策略

## 文档同步要求

以下改动发生时，必须同步更新 `AGENT.md` 与 `CLUADE.md`：

- 支持的新站点发生变化
- CLI 参数发生变化
- base path / alias 规则发生变化
- 输出目录结构发生变化
- PowerShell 包装层调用方式发生变化
- Python 依赖或环境假设发生变化


## 修改意见
- 新增站点时，保持最小改动路径，不要随意修改输出结构或 CLI 参数
- 由于 `spider.ps1` 中的别名展开逻辑，新增站点时需要同步更新 `CLUADE.md` 中的别名展开规则
- 由于项目会变得很复杂所以这次的修改可以考虑把单一的文件拆成多个文件，每个文件负责不同的功能，不过需要有良好的代码结构和注释，方便后续维护，可以考虑成为独立的模块，为以后agent项目(拥有mcp、rag模块)提供爬虫功能，桌面agent调用mcp去使用
- 例如，`spider.py` 可负责处理 Python 逻辑，`spider.ps1` 可负责处理 PowerShell 逻辑
- 需要在 `AGENT.md` 中增加一个章节，介绍如何新增站点的步骤和注意事项，确保后续维护者能够按照规范添加新的爬虫逻辑
- 需要在 `AGENT.md` 中增加一个章节，介绍如何调整输出目录结构，确保后续维护者能够按照规范调整输出目录结构
