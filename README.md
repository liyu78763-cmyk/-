# 跨境电商快讯自动推送到钉钉

这是一个完整可运行的 Python 3.12 项目，用于每个工作日北京时间 10:00 在 GitHub Actions 云端采集最近 24 小时跨境电商新闻；为降低 GitHub 整点定时延迟或漏触发影响，会在 10:00-10:30 做补偿尝试，并用当天 run-key 防止重复发送。程序会硬性排除超过 7 天的旧闻，按热度和来源优先级发送 TOP10；内容不足时按备用策略补位，仍不足则不硬凑。

## 功能

- 默认覆盖 Amazon 美国站、FBA、Amazon Ads、CPSC/FDA/FTC/CBP/USTR、USPS/UPS/FedEx、Walmart Marketplace、TikTok Shop US、Temu、eBay 等主题。
- 默认数据源包括官方 RSS 与 GDELT 新闻搜索；新闻搜索层通过 `NewsProvider` 接口可替换。
- 已接入 AMZ123 跨境早报作为 C 级行业线索来源，优先补充亚马逊和北美相关内容；CPSC/召回类 AMZ123 内容允许进入快讯但仍显示 AMZ123 来源，官方 CPSC 来源抓到时优先级更高。
- 标题下方会显示“今日汇率”，每日从中国人民银行“人民币汇率中间价公告”栏目提取 `1美元对人民币` 中间价；汇率源失败时跳过该块，不影响新闻发送。
- 使用 SQLite 保存已推送 URL 与事件指纹，7 天内不重复推送，30 天后自动清理。
- 即使搜索窗口被调宽，超过 7 天的新闻也会被过滤。
- 支持钉钉机器人加签。
- 长消息会按安全长度拆分。
- 支持 dry-run，本地或 Actions 手动运行时可只生成快讯不发送。
- 单一新闻源失败不会导致整个任务失败。
- 请求均设置超时，并带指数退避重试。
- 日志会遮蔽 Webhook、签名密钥与 API Key。

## 本地安装

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

复制环境变量模板：

```bash
copy .env.example .env
```

PowerShell 临时设置示例：

```powershell
$env:DINGTALK_WEBHOOK="https://oapi.dingtalk.com/robot/send?access_token=xxx"
$env:DINGTALK_SECRET="SECxxx"
$env:AI_API_KEY="sk-xxx"
$env:AI_BASE_URL="https://api.openai.com/v1"
$env:AI_MODEL="gpt-4.1-mini"
```

## 本地运行

只生成快讯，不发送钉钉：

```bash
python -m crossborder_daily --dry-run --output data/latest_report.md
```

使用本地测试新闻夹具：

```bash
python -m crossborder_daily --dry-run --fixture tests/fixtures/sample_news.json --output data/latest_report.md --no-ai
```

真实发送：

```bash
python -m crossborder_daily --output data/latest_report.md
```

## 环境变量

必须从环境变量读取密钥：

- `DINGTALK_WEBHOOK`：钉钉自定义机器人 Webhook。
- `DINGTALK_SECRET`：机器人加签密钥；未开启加签时可留空。
- `AI_API_KEY`：OpenAI-compatible API Key；可选，未配置或无额度时会自动使用固定模板生成快讯。
- `AI_BASE_URL`：OpenAI-compatible API Base URL，例如 `https://api.openai.com/v1`；可选。
- `AI_MODEL`：模型名称；可选。

可选：

- `DINGTALK_MAX_CHARS`：单条钉钉消息最大字符数，默认 `3500`。
- `MIN_HIGH_VALUE_ITEMS`：少于该数量时扩展至 48 小时，默认 `0`，即严格只发近 24 小时 TOP10。
- `MAX_NEWS_AGE_DAYS`：新闻最大年龄，默认 `7` 天。
- `LOG_LEVEL`：默认 `INFO`。

如果需要接入 SerpAPI、Bing News Search、Google Programmable Search、企业内部新闻服务或其他行业资讯站，请新增实现 `src/crossborder_daily/sources/base.py` 中的 `NewsProvider` 接口，并在 `src/crossborder_daily/sources/registry.py` 注册。新增密钥也必须通过 GitHub Secrets 或本地环境变量注入。

## GitHub 部署

1. 将本项目提交到 GitHub 仓库。
2. 在仓库 `Settings -> Secrets and variables -> Actions -> New repository secret` 添加密钥。
3. 确认 `.github/workflows/daily-crossborder-news.yml` 已存在。
4. 工作流按工作日北京时间 `10:00-10:30` 补偿尝试发送；对应 GitHub Actions cron 的 UTC `02:00-02:30`。GitHub Actions 可能会有几分钟排队延迟，但会按当天 `run-key` 防止重复发送。
5. 可在 `Actions -> Cross-border DingTalk Daily` 手动运行；`dry_run=false` 会真实发送，`dry_run=true` 只生成报告不发送。

需要配置的 GitHub Secrets：

- `DINGTALK_WEBHOOK`
- `DINGTALK_SECRET`
- `AI_API_KEY`
- `AI_BASE_URL`
- `AI_MODEL`

历史去重文件 `data/history.sqlite` 会通过 GitHub Actions cache 保存，缓存 key 每次运行唯一，并用 restore-key 恢复最近一次历史文件，避免每次运行丢失去重状态。

## 钉钉机器人配置

1. 在目标钉钉群打开「群设置」。
2. 进入「机器人」并添加「自定义机器人」。
3. 安全设置建议启用「加签」。
4. 复制 Webhook 到 `DINGTALK_WEBHOOK`。
5. 复制加签密钥到 `DINGTALK_SECRET`。
6. 先用 GitHub Actions 的 `dry_run=true` 或本地 `--dry-run` 检查快讯内容，再关闭 dry-run 真实发送。

## 手动测试

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest
```

端到端 dry-run：

```bash
python -m crossborder_daily --dry-run --fixture tests/fixtures/sample_news.json --output data/latest_report.md --no-ai
```

测试时不访问人民银行汇率页：

```bash
python -m crossborder_daily --dry-run --fixture tests/fixtures/sample_news.json --output data/latest_report.md --no-ai --no-exchange-rate
```

## 常见错误

- `DINGTALK_WEBHOOK is required`：未设置 Webhook，或当前不是 `--dry-run`。
- `DingTalk returned error`：检查机器人是否被删除、Webhook 是否正确、关键词/加签安全策略是否匹配。
- `AI request failed`：检查 `AI_BASE_URL` 是否包含 `/v1`、模型名是否可用、API Key 是否有效。
- 快讯新闻少：默认只保留最近 24 小时内通过核验的 TOP10；超过 7 天的旧闻会被过滤，AMZ123 会按备用优先级补位，仍不足时不会硬凑无关内容。
- GitHub Actions 没有发送：检查手动触发是否开启了 `dry_run`，以及 Secrets 是否完整。

## 项目结构

```text
src/                    Python 源码
tests/                  单元测试和 dry-run 端到端测试
data/                   运行时历史库和数据源配置
prompts/                快讯提示词
.github/workflows/      GitHub Actions 定时任务
```
