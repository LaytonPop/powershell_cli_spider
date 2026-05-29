# CLUADE.md

本文件面向使用 Claude 类助手维护该仓库时的快速协作约定。内容尽量短、可执行、贴近当前代码，而不是通用模板。

## 先读什么

进入仓库后，优先阅读：

- `spider.py`
- `spider.ps1`

这个项目没有复杂目录结构，绝大多数真实行为都在这两个文件里。

## 项目一句话

这是一个 Windows 终端爬虫工具，用来把微信公众号和知乎文章抓取到本地知识库目录，并把图片一并保存到文章目录下。

## 当前事实

- 默认知识库根目录是 `F:\workspace3\wen\Repository\obsidianDB`
- PowerShell 入口依赖固定 Python：
  - `C:\Users\morganWen\.conda\envs\spider\python.exe`
- 当前支持输出：
  - `html`
  - `md`
- 当前支持站点：
  - `mp.weixin.qq.com`
  - `zhuanlan.zhihu.com`
  - `www.zhihu.com/question`
- 批量抓取只在 `spider.ps1` 中实现

## 你在修改时要守住的行为

- 输入一个 URL 后，最终应在知识库中生成“文章目录 + 主文件 + images 子目录”
- Markdown 输出必须继续保留 frontmatter
- 图片链接必须继续改写为本地相对路径
- `-f` 目录参数必须继续支持别名展开：
  - `A -> 001-Current_Projects`
  - `B -> 002-raw_resource`
  - `c -> 003-wiki_schema`
- PowerShell 入口的“位置参数就是 URL”行为不要随意破坏
- PowerShell 入口的批量抓取功能不要随意破坏
这是实际的开发目标但是因为上一次修改的时候弄错了，所以你需要修改这部分的CLI参数：
```powershell
spider.ps1 -u https://www.zhihu.com/question/362222222 -f A -o md
```

## 高风险区域

- `ZhihuScraper.match()` 放得比解析逻辑更宽，可能匹配到当前 DOM 不兼容的知乎问题页
- `spider.ps1` 中的 Python 路径和脚本路径是硬编码的，改动会直接影响用户日常调用
- 没有测试框架，改 selector 或输出格式时很容易产生静默回归
- 图片下载不会重试，网络稍差时可能导致正文正常、图片缺失

## 常见任务怎么做

### 新增站点

- 在 `spider.py` 中新增一个 `AbstractScraper` 子类
- 保持 `scrape()` 返回统一字段：
  - `title`
  - `html_content`
  - `publish_time`
  - `source_url`
- 注册到 `SCRAPERS`
- 如果该站点图片使用特殊属性，补 `_download_and_rewrite()`

### 调整输出目录逻辑

- 先检查 `BASES`
- 再检查 `ALIASES`
- 最后检查 `resolve_output_dir()`
- 若目录结构变化，务必同步更新 `spider.ps1` 的帮助文本和两个文档

### 调整命令行参数

- Python CLI 改动后，检查 `spider.ps1` 是否还在正确传参
- 特别关注：
  - `-u/--url`
  - `-f/--folder`
  - `-o/--format`
  - `--dry-run`

## 建议的最小验证

如果本次修改不涉及联网逻辑，至少做这些检查：

```powershell
python .\spider.py --help
python .\spider.py --list-bases
python .\spider.py --list-aliases
python .\spider.py --dry-run -f A-Current_Projects -f Demo -o md
```

如果改了 `spider.ps1`，再补一次：

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
