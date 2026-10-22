# CLUADE.md

本文件是使用 Claude 类助手维护本仓库时的最短协作约定。完整架构与行为约束看 `AGENT.md`，用户用法看 `README.md`。

文件名 `CLUADE.md` 是有意保留的；如需对齐社区习惯再改名为 `CLAUDE.md`。

## 先读

1. `README.md`（用户视角：参数、配置、FAQ）
2. `AGENT.md`（架构、不变量、验证命令）
3. 改动点对应模块：`spider_core/cli.py`、`config.py`、`service.py`、`errors.py`、`scrapers/`、`media.py`、`renderers.py`、`html_cleaner.py`

## 硬规则

- Python CLI（`spider_core/cli.py`）是唯一参数解析源；`spider.ps1` / `spider.sh` 只负责找 Python 并转发参数，禁止在其中重新实现参数解析。
- 旧参数已断代（`-u/--url`、`-df`、`-f`、`--batch-file`）：不要静默恢复兼容，只保留迁移报错。
- 抓取失败必须抛 `SpiderError` 子类（`NetworkError` / `ParseError` / `UnsupportedURLError`），由 `service.save_article` 收进 `SaveResult.error`，不要返回 `None` 吞掉失败。
- 同名文章目录已存在时用 `_2`、`_3` 后缀新建，不得覆盖旧文章。
- HTML 输出必须清除 `visibility` / `opacity` / 正文根节点 `display:none`，否则会回归"打开空白"。
- Markdown 的 YAML frontmatter 与图片本地化行为不能破坏；默认格式是 `md`，默认落点是 `000-inbox`。
- 知识库路径只来自 `spider.config.toml`（或 `--config`/`SPIDER_CONFIG`/`SPIDER_VAULT`，旧 `SPIDER_BASE` 仅作兼容回退），不要重新硬编码盘符。
- 改动 CLI、输出结构或路径规则时，同步更新 `README.md`、`AGENT.md` 与本文件。

## 验证

```powershell
python -m unittest discover -s tests -v    # 当前 103 个用例
python .\spider.py --help
python .\spider.py --list-bases
python .\spider.py --dry-run "https://mp.weixin.qq.com/s/xxx" -d A/IoT -F both
.\spider.ps1 --version
```

```bash
./spider.sh --version
```

改了选择器 / 渲染 / 图片逻辑时，必须做一次真实抓取（`-o tmp_out\... -F both`），并确认产物 html 中没有 `visibility`/`opacity`、图片为本地 `images/` 路径。

## 代码偏好

- 保持当前模块划分，优先小而准的修改，不要把逻辑堆回 `spider.py`。
- 新增行为先补测试（`tests/`，标准库 unittest），再改实现。
- 不引入新依赖，除非明确解释收益并更新 `requirements.txt`。
