# Codex 交接文档 — Daily Briefing 项目

## 项目概述

自动化日报推送系统，每天早/午定时抓取资讯 + AI 生成内容，通过飞书推送给用户。

- **GitHub 仓库**: `https://github.com/jiajia0820/daily-briefing`
- **默认分支**: `main`（本地分支为 `master`，push 时用 `git push origin master:main`）
- **运行环境**: GitHub Actions (ubuntu-latest, Python 3.11)
- **定时触发**: cron-job.org → GitHub `repository_dispatch` API（精确到分钟）
- **推送渠道**: 飞书应用消息（不是 webhook，是飞书自建应用 + open_id 单聊推送）

---

## 架构与数据流

```
[cron-job.org] --repository_dispatch--> [GitHub Actions]
                                            │
                    ┌───────────────────────┤
                    ▼                       ▼
              morning.py              afternoon.py
                    │                       │
        ┌───────────┤               ┌───────┤
        ▼           ▼               ▼       ▼
   RSS/知乎/B站   天气/播客       GPT生成   GitHub热门
   GPT选稿        每日一句       知识卡片   AI摘要
        │           │               │       │
        └─────┬─────┘               └───┬───┘
              ▼                         ▼
        build_morning_card()     build_afternoon_card()
              │                         │
              └──────────┬──────────────┘
                         ▼
                  send_feishu_card()
                         │
                         ▼
                    飞书用户收到卡片消息
```

---

## 目录结构（精确到文件）

```
daily-briefing/
├── .github/workflows/
│   ├── morning.yml              # 早报 workflow（repository_dispatch: morning）
│   └── afternoon.yml            # 午报 workflow（repository_dispatch: afternoon）
├── config/
│   ├── config.yaml              # 主配置（城市、兴趣、LLM、天气、飞书、去重）
│   ├── rss_sources.yaml         # RSS 源 + 播客源（播客源已不再使用，保留兼容）
│   └── quotes.json              # 名言库（本地 JSON）
├── src/
│   ├── morning.py               # 早报入口 main()
│   ├── afternoon.py             # 午报入口 main()
│   ├── fetchers/
│   │   ├── rss_fetcher.py       # RSS 抓取（feedparser）
│   │   ├── zhihu_fetcher.py     # 知乎热榜（tophub.today 抓取）
│   │   ├── bilibili_fetcher.py  # B站热门视频（官方 API）
│   │   ├── weather_fetcher.py   # 和风天气 API（GEO+实时+3天预报）
│   │   ├── quote_fetcher.py     # 每日一句（本地 quotes.json 随机）
│   │   ├── podcast_fetcher.py   # 播客推荐（Apple Podcasts 中国区热榜）
│   │   └── github_fetcher.py    # GitHub Trending 爬虫（BeautifulSoup）
│   ├── processors/
│   │   ├── llm_selector.py      # GPT 选稿（从候选文章中挑 top N）
│   │   └── llm_generator.py     # GPT 生成午报内容 + GitHub 项目摘要
│   ├── publishers/
│   │   └── feishu.py            # 飞书卡片构建 + 推送（应用消息模式）
│   └── utils/
│       ├── llm_client.py        # OpenAI chat_completion 封装
│       ├── web_searcher.py      # Bing 搜索（知乎/小红书链接）
│       ├── dedup.py             # 文章去重（JSON 文件存储）
│       └── logger.py            # 日志工具
├── data/                        # 运行时数据（去重记录、播客历史、主题历史）
│   ├── seen_articles.json       # 已推送文章去重
│   ├── podcast_history.json     # 已推荐播客集数
│   └── generated_topics_*.json  # 午报已用主题去重
├── .env.example                 # 环境变量模板
├── requirements.txt             # Python 依赖
└── README.md                    # 项目说明（需要更新）
```

---

## 核心模块说明

### 早报 `src/morning.py`
1. RSS 抓取（11 个源）→ 知乎热榜 → 兴趣领域 RSS
2. 去重过滤（7 天窗口）
3. GPT 选稿（全行业 5 条 + 兴趣领域 5 条）
4. B站热门视频（5 条）
5. 天气（和风天气 API，自定义 host）
6. 每日一句（本地 JSON 随机）
7. 播客推荐（Apple Podcasts 中国区科技/商务/教育/新闻热榜，去重轮换）
8. 组装飞书卡片 → 推送

### 午报 `src/afternoon.py`
1. GPT 生成 3 条知识卡片（AI 技巧 / 心理学经济学 / 品牌洞察）
2. 每条卡片附带知乎 + B站延伸阅读链接
3. GitHub Trending 前 5 项目 + GPT 中文摘要
4. 组装飞书卡片 → 推送

### 播客推荐 `src/fetchers/podcast_fetcher.py`
- **数据源**: Apple Podcasts RSS Marketing API（无需认证）
- **分类**: genre 1318(科技) 1321(商务) 1304(教育) 1489(新闻)
- **去重**: `data/podcast_history.json` 记录已推荐的 ep_id，最多 100 条
- **轮换**: 每次从热榜未推荐的中选第一个，推完后自动重置
- **注意**: `rss_sources.yaml` 中的 `podcast` 配置已不再使用（旧的小宇宙模式），但保留向后兼容。`fetch_podcast()` 的 `sources` 参数现在是可选的。

### 飞书推送 `src/publishers/feishu.py`
- **模式**: 飞书自建应用（app mode），不是 webhook
- **认证**: app_id + app_secret → 获取 tenant_access_token → 发送消息
- **接收者**: open_id 单聊推送
- **卡片格式**: 飞书 Interactive Card JSON

### LLM 调用 `src/utils/llm_client.py`
- **模型**: gpt-5.5（通过自定义 base_url 代理）
- **API 代理**: 用户使用自定义 OpenAI 兼容端点，通过 `OPENAI_BASE_URL` 环境变量配置
- **所有 LLM 调用**都经过 `chat_completion()` 函数

---

## 环境变量 / Secrets

GitHub Actions Secrets（6 个）：

| Secret | 说明 | 当前状态 |
|--------|------|---------|
| `OPENAI_API_KEY` | OpenAI 兼容 API Key | ✅ 已配置 |
| `OPENAI_BASE_URL` | API 代理地址（用户自定义） | ✅ 已配置 |
| `FEISHU_APP_ID` | 飞书应用 App ID | ✅ 已配置 |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret | ✅ 已配置 |
| `FEISHU_RECEIVE_ID` | 飞书接收者 open_id | ✅ 已配置 |
| `QWEATHER_API_KEY` | 和风天气 API Key（注意不是 host） | ✅ 已配置 |

本地开发用 `.env` 文件，格式见 `.env.example`。

---

## 定时触发配置

- **平台**: cron-job.org（免费）
- **触发方式**: POST `https://api.github.com/repos/jiajia0820/daily-briefing/dispatches`
- **认证**: GitHub Fine-grained PAT（需要 Contents read/write 权限）
- **Headers**: Authorization: Bearer {token}, Content-Type: application/json, Accept: application/vnd.github.v3+json
- **早报 Body**: `{"event_type":"morning"}` — 每天 07:00 CST
- **午报 Body**: `{"event_type":"afternoon"}` — 每天 12:00 CST
- **⚠️ 注意**: 用户的 PAT 已泄露在聊天记录中，需要重新生成

---

## 已知问题与待优化

### 必须修复
1. **README.md 过时** — 内容与实际功能不匹配（缺少 GitHub 热门、播客改版、B站、定时触发等说明）
2. **rss_sources.yaml 中 podcast 配置冗余** — 播客已改为 Apple Podcasts 热榜，旧配置可删除
3. **.env.example 缺少 OPENAI_BASE_URL** — 需要补充
4. **body.json 残留** — 根目录有测试残留文件，需删除并加入 .gitignore

### 面向开源优化（用户明确提出的方向）
1. **README 重写** — 功能截图、部署教程、配置说明、架构图
2. **配置模板化** — 让用户自定义推送模块（开关早报/午报各板块）
3. **多推送渠道** — 支持飞书 webhook、企业微信、Telegram、邮件等
4. **Docker 支持** — Dockerfile + docker-compose
5. **敏感信息清理** — 确认 `.gitignore` 覆盖 `.env`、`data/`、`__pycache__/`
6. **i18n** — README 中英双语

### 可优化的功能
1. **播客推荐** — 当前 Apple Podcasts 热榜覆盖 4 个分类，可以让用户自定义分类
2. **GitHub Trending** — 可以按语言/时间范围筛选
3. **午报主题去重** — `generated_topics_*.json` 文件会无限增长，需要清理策略
4. **错误处理** — 部分 fetcher 失败时静默降级，可以在卡片中显示"获取失败"提示
5. **测试** — 目前没有单元测试

---

## 本地开发与测试

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实的 API Key

# 运行早报
python src/morning.py

# 运行午报
python src/afternoon.py

# 单独测试播客推荐
python -c "from src.fetchers.podcast_fetcher import fetch_podcast; print(fetch_podcast())"

# 单独测试天气
python -c "from src.fetchers.weather_fetcher import fetch_weather; import os; from dotenv import load_dotenv; load_dotenv(); print(fetch_weather('鼓楼', api_key=os.getenv('QWEATHER_API_KEY'), api_host='jt52qd3e2a.re.qweatherapi.com'))"
```

---

## Git 工作流

```bash
# 本地分支是 master，远端默认分支是 main
git add -A
git commit -m "your message"
git push origin master:main
```

---

## 关键设计决策记录

1. **飞书应用模式 vs Webhook**: 选了应用模式（支持卡片交互和私聊推送），不是群 webhook
2. **播客从小宇宙固定 → Apple 热榜**: 小宇宙无公开 API，Apple Podcasts Chart API 免费且实时
3. **定时从 GitHub cron → cron-job.org**: GitHub Actions cron 延迟 10-30 分钟，外部触发精确到分钟
4. **LLM 模型**: gpt-5.5，通过自定义 base_url 代理调用，不是直连 OpenAI
5. **知乎热榜**: 官方 API 需认证，改用 tophub.today 页面抓取
6. **小红书/抖音**: 搜索引擎不收录，无法爬取，改用 B站视频搜索
