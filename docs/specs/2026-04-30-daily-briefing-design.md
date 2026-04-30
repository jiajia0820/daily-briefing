# Daily Briefing — 设计文档

**日期**：2026-04-30
**状态**：待审核

---

## 1. 项目概述

一个个性化日报推送系统，每天自动抓取资讯、生成内容，通过飞书推送。开源可配置，用户 fork 后修改 YAML 即可使用。

### 核心价值

- **早报**：精选全行业 + 兴趣领域资讯、播客推荐、天气、每日一句
- **午报**：AI 生成知识卡片（AI 技巧、心理学/经济学、品牌洞察）
- **零成本运行**：GitHub Actions 定时触发
- **开源可配置**：YAML 配置兴趣领域、RSS 源、推送渠道

---

## 2. 用户画面

### 早报（每日 8:00 推送到飞书）

```
☀️ 早报 · 2026年4月30日 · 北京 晴 28°C

━━ 全行业资讯 ━━
1. OpenAI 发布 GPT-5 → [原文链接]
2. 苹果 WWDC 2026 日期确认 → [原文链接]
3. 美团无人机配送覆盖 50 城 → [原文链接]
4. 拼多多海外营收首次超过国内 → [原文链接]
5. 小米汽车月交付突破 3 万台 → [原文链接]

━━ AI · 兴趣领域 ━━
1. Claude 4 发布：推理能力大幅提升 → [原文链接]
2. Manus 开源 Agent 框架 → [原文链接]
3. 国内首个 AI 招聘官通过图灵测试 → [原文链接]
4. DeepSeek 发布多模态大模型 → [原文链接]
5. AI 面试官在字节跳动大规模落地 → [原文链接]

━━ 播客推荐 ━━
🎙️ 硅谷101 · 《AI Agent 改变招聘行业》 → [小宇宙链接]

━━ 每日一句 ━━
"The best way to predict the future is to invent it." — Alan Kay

━━ 今日待办 ━━
📝 点击填写今日待办（预留，后续实现）
```

### 午报（每日 12:00 推送到飞书）

```
🧠 午报 · 2026年4月30日

━━ AI 技巧 ━━
Prompt 链式思考：把复杂问题拆成 3 步提问，准确率提升 40%。
先让 AI 列出思考步骤，再逐步执行，避免一次性给出错误答案。
📖 延伸阅读 → [链接]

━━ 心理学技巧 ━━
锚定效应：人们做决策时会过度依赖最先获得的信息。
谈判时先出价的人往往占优势，因为对方会围绕这个"锚"调整。
📖 延伸阅读 → [链接]

━━ 品牌洞察 ━━
Notion 的增长策略：用免费模板生态构建护城河。
他们没有做广告，而是让用户自发创建和分享模板，形成网络效应。
📖 延伸阅读 → [链接]
```

---

## 3. 技术架构

### 技术栈

| 层面 | 选型 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | RSS/LLM 生态最丰富 |
| LLM | OpenAI GPT-4o-mini | 用户已有 Key，选稿用 mini 足够 |
| 定时触发 | GitHub Actions cron | 零成本零运维 |
| 推送 | 飞书 Webhook 机器人 | 支持消息卡片，免费 |
| 配置 | YAML | 用户 fork 后改配置即可 |

### 项目结构

```
daily-briefing/
├── config/
│   ├── config.yaml              # 主配置
│   ├── rss_sources.yaml         # RSS 源清单
│   └── quotes.json              # 名言/网络热梗库
├── src/
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── rss_fetcher.py       # RSS 抓取（feedparser）
│   │   ├── zhihu_fetcher.py     # 知乎热榜 API
│   │   ├── podcast_fetcher.py   # 小宇宙播客
│   │   └── weather_fetcher.py   # 和风天气 API
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── llm_selector.py      # GPT 选稿打分
│   │   └── llm_generator.py     # GPT 生成午报内容
│   ├── publishers/
│   │   ├── __init__.py
│   │   └── feishu.py            # 飞书卡片消息推送
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── dedup.py             # 去重（seen_articles.json）
│   │   └── logger.py            # 日志
│   ├── morning.py               # 早报主流程
│   └── afternoon.py             # 午报主流程
├── templates/
│   ├── morning_card.json        # 飞书早报卡片模板
│   └── afternoon_card.json      # 飞书午报卡片模板
├── data/
│   └── seen_articles.json       # 已推送文章记录（git 持久化）
├── .github/
│   └── workflows/
│       ├── morning.yaml         # 早报 cron（每天 8:00 CST）
│       └── afternoon.yaml       # 午报 cron（每天 12:00 CST）
├── .env.example                 # 环境变量示例
├── config.example.yaml          # 配置示例
├── requirements.txt
├── LICENSE
└── README.md
```

### 数据流

```
早报流水线（morning.py）
════════════════════════════════════════════

┌─────────────┐     ┌─────────────┐
│ RSS 源 ×8+  │────▶│             │
└─────────────┘     │  文章池     │
┌─────────────┐     │  (50+ 篇)  │
│ 知乎热榜    │────▶│             │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ 去重过滤    │  seen_articles.json
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼                         ▼
    ┌─────────────────┐     ┌─────────────────┐
    │ GPT 选稿        │     │ GPT 选稿        │
    │ 全行业 Top 5    │     │ 兴趣领域 Top 5  │
    └────────┬────────┘     └────────┬────────┘
             │                       │
             └───────────┬───────────┘
                         │
    ┌────────────┐       │       ┌────────────┐
    │ 小宇宙播客 │───┐   │   ┌───│ 天气 API   │
    └────────────┘   │   │   │   └────────────┘
    ┌────────────┐   │   │   │   ┌────────────┐
    │ 每日一句   │───┤   │   ├───│ quotes.json│
    └────────────┘   │   │   │   └────────────┘
                     ▼   ▼   ▼
               ┌─────────────────┐
               │ 组装飞书卡片    │
               └────────┬────────┘
                        ▼
               ┌─────────────────┐
               │ 飞书 Webhook    │
               └─────────────────┘


午报流水线（afternoon.py）
════════════════════════════════════════════

┌──────────────────┐
│ GPT 生成         │
│ · AI 技巧        │──▶ 短文 + 延伸链接
│ · 心理学/经济学  │──▶ 短文 + 延伸链接
│ · 品牌洞察       │──▶ 短文 + 延伸链接
└────────┬─────────┘
         ▼
┌─────────────────┐
│ 组装飞书卡片    │
└────────┬────────┘
         ▼
┌─────────────────┐
│ 飞书 Webhook    │
└─────────────────┘
```

---

## 4. 模块详细设计

### 4.1 fetchers — 数据获取层

#### rss_fetcher.py

- **输入**：`rss_sources.yaml` 中的源列表
- **输出**：`List[Article]`，每篇包含 `title, url, source, published_at, category`
- **依赖**：`feedparser` 库
- **容错**：单个源超时（10s）或异常 → 跳过，记录日志，不影响其他源

#### zhihu_fetcher.py

- **输入**：无（直接抓热榜）
- **输出**：`List[Article]`
- **方式**：请求知乎热榜非官方 API（`https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total`）
- **容错**：API 不可用 → 跳过知乎，日志记录

#### podcast_fetcher.py

- **输入**：`rss_sources.yaml` 中的播客 RSS 源
- **输出**：`List[Podcast]`，包含 `name, episode_title, xiaoyuzhoufm_url`
- **方式**：小宇宙 RSS 源解析，或 RSSHub 转换
- **容错**：同上

#### weather_fetcher.py

- **输入**：`config.yaml` 中的城市
- **输出**：`WeatherInfo`，包含 `city, temp, condition, icon`
- **依赖**：和风天气免费 API
- **容错**：API 不可用 → 显示"天气获取失败"

### 4.2 processors — 处理层

#### llm_selector.py

- **输入**：`List[Article]` + 兴趣配置
- **输出**：全行业 Top 5 + 每个兴趣领域 Top 5（仅 title + url）
- **Prompt 策略**：
  ```
  你是一位资深新闻编辑。从以下文章中选出最有价值的 5 篇。
  评判标准：影响力、时效性、信息增量。
  只返回 JSON 数组：[{"title": "...", "url": "..."}]
  ```
- **模型**：GPT-4o-mini（便宜、速度快、选稿足够）
- **成本估算**：每次约 50 篇标题 ≈ 2000 tokens 输入，约 $0.001/次

#### llm_generator.py

- **输入**：午报主题类型（AI技巧 / 心理学 / 品牌洞察）
- **输出**：短文（100-150 字） + 延伸阅读链接
- **Prompt 策略**：
  ```
  生成一条简洁实用的 [AI技巧]，100 字以内。
  要求：有具体方法、可立即使用、附一个延伸阅读链接。
  避免重复最近 7 天的主题：[历史主题列表]
  ```
- **去重**：维护 `data/generated_topics.json` 记录近 30 天已生成主题

### 4.3 publishers — 推送层

#### feishu.py

- **输入**：组装好的卡片数据
- **输出**：HTTP POST 到飞书 Webhook
- **格式**：飞书 Interactive Card（支持 Markdown、分栏、链接按钮）
- **容错**：推送失败 → 重试 2 次，间隔 5s

### 4.4 utils — 工具层

#### dedup.py

- **存储**：`data/seen_articles.json`，记录已推送文章 URL 的 SHA256 hash
- **保留**：最近 7 天的记录，自动清理更早的
- **持久化**：GitHub Actions 中通过 git commit + push 写回仓库

#### logger.py

- 统一日志格式：`[2026-04-30 08:00:01] [INFO] [rss_fetcher] 36氪: 获取 15 篇文章`
- 错误日志：`[ERROR] [zhihu_fetcher] 请求超时，已跳过`

---

## 5. 配置设计

### config.yaml

```yaml
user:
  city: "北京"

interests:
  - name: "AI"
    keywords: ["人工智能", "大模型", "LLM", "AI Agent", "GPT", "深度学习"]
  - name: "企业招聘"
    keywords: ["招聘", "HR", "人才", "求职", "用工", "面试", "猎头"]

schedule:
  morning: "08:00"
  afternoon: "12:00"
  timezone: "Asia/Shanghai"

publisher:
  feishu:
    webhook_url: "${FEISHU_WEBHOOK}"

llm:
  provider: "openai"
  model: "gpt-4o-mini"
  api_key: "${OPENAI_API_KEY}"

weather:
  provider: "qweather"
  api_key: "${QWEATHER_API_KEY}"

dedup:
  retention_days: 7
```

### rss_sources.yaml

```yaml
general:
  - name: "36氪"
    url: "https://36kr.com/feed"
    category: "科技商业"
  - name: "虎嗅"
    url: "https://www.huxiu.com/rss/0.xml"
    category: "商业深度"
  - name: "少数派"
    url: "https://sspai.com/feed"
    category: "科技生活"
  - name: "极客公园"
    url: "https://www.geekpark.net/rss"
    category: "科技前沿"
  - name: "澎湃新闻"
    url: "https://www.thepaper.cn/rss_newslist.jsp"
    category: "时政财经"
  - name: "界面新闻"
    url: "https://www.jiemian.com/rss.html"
    category: "财经商业"
  - name: "IT之家"
    url: "https://www.ithome.com/rss/"
    category: "科技快讯"
  - name: "爱范儿"
    url: "https://www.ifanr.com/feed"
    category: "消费科技"

ai:
  - name: "机器之心"
    url: "https://www.jiqizhixin.com/rss"
    category: "AI"
  - name: "量子位"
    url: "https://www.qbitai.com/feed"
    category: "AI"

podcast:
  - name: "硅谷101"
    url: "https://feed.xyzfm.space/xxxx"
    platform: "xiaoyuzhoufm"
  - name: "What's Next|科技早知道"
    url: "https://feed.xyzfm.space/xxxx"
    platform: "xiaoyuzhoufm"
```

---

## 6. GitHub Actions 设计

### morning.yaml

```yaml
name: Morning Briefing
on:
  schedule:
    - cron: '0 0 * * *'    # UTC 00:00 = CST 08:00
  workflow_dispatch:         # 手动触发（调试用）

jobs:
  morning:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python src/morning.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          FEISHU_WEBHOOK: ${{ secrets.FEISHU_WEBHOOK }}
          QWEATHER_API_KEY: ${{ secrets.QWEATHER_API_KEY }}
      - name: Commit dedup data
        run: |
          git config user.name "daily-briefing-bot"
          git config user.email "bot@daily-briefing"
          git add data/
          git diff --cached --quiet || git commit -m "chore: update seen articles"
          git push
```

---

## 7. 容错设计

| 故障场景 | 处理方式 |
|---------|---------|
| 单个 RSS 源不可用 | 跳过该源，日志记录，继续处理其他源 |
| 知乎 API 不可用 | 跳过知乎，仅从 RSS 源选稿 |
| 天气 API 不可用 | 卡片中显示"天气暂不可用" |
| OpenAI API 不可用 | 跳过 LLM 选稿，按时间倒序取最新 5 篇（降级） |
| 飞书推送失败 | 重试 2 次（间隔 5s），仍失败则日志记录 |
| 所有源均不可用 | 不推送，日志记录异常 |

---

## 8. 成本估算

| 项目 | 费用 |
|------|------|
| GitHub Actions | 免费（每月 2000 分钟，每天 2 次约用 10 分钟/月） |
| OpenAI GPT-4o-mini | 约 $0.01/天（选稿 + 生成，极低） |
| 和风天气 API | 免费（每日 1000 次） |
| 飞书机器人 | 免费 |
| **总计** | **约 $0.3/月** |

---

## 9. 开发计划

| 阶段 | 内容 | 交付物 |
|------|------|--------|
| P1 | RSS 抓取 + 知乎热榜 + GPT 选稿 + 飞书推送 | 早报资讯部分可用 |
| P2 | 天气 + 每日一句 + 播客推荐 | 完整早报 |
| P3 | 午报 GPT 生成内容 | 完整午报 |
| P4 | 飞书卡片美化 + 去重机制 | 体验优化 |
| P5 | README + 配置文档 + LICENSE | GitHub 开源发布 |

---

## 10. 不在 MVP 范围内（后续考虑）

- 今日待办交互功能
- 微信渠道推送
- 多语言支持
- Web 管理后台
- 阅读数据统计
