# Daily Briefing 实现计划

> 归档说明：这是项目早期实现计划，已经过时，仅用于追溯历史。当前部署和配置请以仓库根目录 `README.md`、`config/config.example.yaml` 和 `.env.example` 为准。

> **For agentic workers:** Execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个基于 GitHub Actions 的个性化日报推送系统，通过飞书推送早报和午报。

**Architecture:** Python 脚本通过 RSS + API 抓取资讯，GPT-4o-mini 选稿/生成内容，飞书 Webhook 推送卡片消息。GitHub Actions cron 定时触发。YAML 配置驱动，开源可 fork。

**Tech Stack:** Python 3.11+, feedparser, openai, requests, PyYAML, GitHub Actions

---

## P1: 核心链路 — RSS + GPT 选稿 + 飞书推送

### Task 1: 项目骨架 + 依赖

**Files:**
- Create: `requirements.txt`
- Create: `src/__init__.py`
- Create: `src/fetchers/__init__.py`
- Create: `src/processors/__init__.py`
- Create: `src/publishers/__init__.py`
- Create: `src/utils/__init__.py`
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: 创建 requirements.txt**

```
feedparser==6.0.11
openai>=1.30.0
requests>=2.31.0
PyYAML>=6.0.1
python-dotenv>=1.0.0
```

- [ ] **Step 2: 创建 .gitignore**

```
__pycache__/
*.pyc
.env
.venv/
venv/
*.egg-info/
dist/
build/
.idea/
.vscode/
```

- [ ] **Step 3: 创建 .env.example**

```
OPENAI_API_KEY=your-openai-api-key
FEISHU_WEBHOOK=your-feishu-webhook-url
QWEATHER_API_KEY=your-qweather-key
```

- [ ] **Step 4: 创建所有 __init__.py**

全部为空文件。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: project skeleton and dependencies"
```

---

### Task 2: YAML 配置文件

**Files:**
- Create: `config/config.yaml`
- Create: `config/rss_sources.yaml`
- Create: `config/quotes.json`

- [ ] **Step 1: 创建 config/config.yaml**

```yaml
user:
  city: "北京"

interests:
  - name: "AI"
    keywords: ["人工智能", "大模型", "LLM", "AI Agent", "GPT", "深度学习", "机器学习", "Claude", "OpenAI"]
  - name: "企业招聘"
    keywords: ["招聘", "HR", "人才", "求职", "用工", "面试", "猎头", "人力资源", "校招", "社招"]

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

- [ ] **Step 2: 创建 config/rss_sources.yaml**

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
```

- [ ] **Step 3: 创建 config/quotes.json**

包含初始名言库（30+ 条）。

- [ ] **Step 4: Commit**

```bash
git add config/
git commit -m "chore: add configuration files"
```

---

### Task 3: 日志工具

**Files:**
- Create: `src/utils/logger.py`

- [ ] **Step 1: 实现 logger.py**

统一日志格式：`[时间] [级别] [模块] 消息`。提供 `get_logger(name)` 函数。

- [ ] **Step 2: Commit**

```bash
git add src/utils/
git commit -m "feat: add logger utility"
```

---

### Task 4: RSS 抓取器

**Files:**
- Create: `src/fetchers/rss_fetcher.py`

- [ ] **Step 1: 实现 rss_fetcher.py**

```python
def fetch_rss(sources: list[dict]) -> list[dict]:
    """
    输入：RSS 源列表 [{name, url, category}]
    输出：文章列表 [{title, url, source, category, published_at}]
    容错：单个源超时(10s)或异常 → 跳过，记录日志
    """
```

- [ ] **Step 2: 本地测试 — 抓取 36氪**

```bash
python -c "from src.fetchers.rss_fetcher import fetch_rss; print(fetch_rss([{'name': '36氪', 'url': 'https://36kr.com/feed', 'category': '科技商业'}])[:2])"
```

- [ ] **Step 3: Commit**

```bash
git add src/fetchers/
git commit -m "feat: add RSS fetcher"
```

---

### Task 5: 知乎热榜抓取器

**Files:**
- Create: `src/fetchers/zhihu_fetcher.py`

- [ ] **Step 1: 实现 zhihu_fetcher.py**

```python
def fetch_zhihu_hot() -> list[dict]:
    """
    输出：热榜文章列表 [{title, url, source: "知乎热榜", category: "热榜"}]
    容错：API 不可用 → 返回空列表，记录日志
    """
```

- [ ] **Step 2: 本地测试**

```bash
python -c "from src.fetchers.zhihu_fetcher import fetch_zhihu_hot; print(fetch_zhihu_hot()[:3])"
```

- [ ] **Step 3: Commit**

```bash
git add src/fetchers/
git commit -m "feat: add Zhihu hot list fetcher"
```

---

### Task 6: GPT 选稿器

**Files:**
- Create: `src/processors/llm_selector.py`

- [ ] **Step 1: 实现 llm_selector.py**

```python
def select_articles(articles: list[dict], category: str, keywords: list[str], count: int = 5) -> list[dict]:
    """
    输入：文章列表 + 选稿类别/关键词
    输出：Top N 文章 [{title, url}]
    降级：OpenAI 不可用 → 按时间倒序取最新 N 篇
    """
```

Prompt 策略：传入文章标题列表，让 GPT 按影响力/时效性/信息增量打分，返回 JSON。

- [ ] **Step 2: 本地测试（需要 OPENAI_API_KEY）**

```bash
python -c "
from src.processors.llm_selector import select_articles
articles = [{'title': '测试文章1', 'url': 'http://example.com/1'}, {'title': '测试文章2', 'url': 'http://example.com/2'}]
print(select_articles(articles, 'general', [], 2))
"
```

- [ ] **Step 3: Commit**

```bash
git add src/processors/
git commit -m "feat: add LLM article selector"
```

---

### Task 7: 飞书推送器

**Files:**
- Create: `src/publishers/feishu.py`
- Create: `templates/morning_card.json`

- [ ] **Step 1: 实现 feishu.py**

```python
def send_feishu_card(webhook_url: str, card: dict) -> bool:
    """
    输入：webhook URL + 飞书卡片 JSON
    输出：成功/失败
    容错：失败重试 2 次，间隔 5s
    """

def build_morning_card(general_news, interest_news, interests_name) -> dict:
    """
    组装早报飞书卡片
    """
```

- [ ] **Step 2: 创建 templates/morning_card.json 模板**

飞书 Interactive Card 模板结构。

- [ ] **Step 3: Commit**

```bash
git add src/publishers/ templates/
git commit -m "feat: add Feishu card publisher"
```

---

### Task 8: 早报主流程（P1 版本）

**Files:**
- Create: `src/morning.py`

- [ ] **Step 1: 实现 morning.py**

```python
def main():
    # 1. 加载配置
    # 2. 抓取 RSS + 知乎
    # 3. GPT 选稿：全行业 Top5 + 兴趣领域 Top5
    # 4. 组装飞书卡片
    # 5. 推送
```

- [ ] **Step 2: 本地端到端测试**

```bash
python src/morning.py
```

验证：飞书群收到早报消息。

- [ ] **Step 3: Commit**

```bash
git add src/morning.py
git commit -m "feat: morning briefing P1 — news selection + feishu push"
```

---

## P2: 补全早报 — 天气 + 每日一句 + 播客

### Task 9: 天气抓取器

**Files:**
- Create: `src/fetchers/weather_fetcher.py`

- [ ] **Step 1: 实现 weather_fetcher.py**

```python
def fetch_weather(city: str, api_key: str) -> dict:
    """
    输出：{city, temp, condition, icon}
    容错：API 不可用 → 返回 {city, temp: "--", condition: "暂不可用"}
    """
```

- [ ] **Step 2: 本地测试**
- [ ] **Step 3: Commit**

---

### Task 10: 每日一句

**Files:**
- Create: `src/fetchers/quote_fetcher.py`

- [ ] **Step 1: 实现 quote_fetcher.py**

从 `config/quotes.json` 随机选取，按日期 hash 保证同一天同一句。

- [ ] **Step 2: Commit**

---

### Task 11: 播客抓取器

**Files:**
- Create: `src/fetchers/podcast_fetcher.py`

- [ ] **Step 1: 实现 podcast_fetcher.py**

解析小宇宙 RSS，提取最新单集名 + 链接。

- [ ] **Step 2: Commit**

---

### Task 12: 完善早报主流程

**Files:**
- Modify: `src/morning.py`
- Modify: `src/publishers/feishu.py`

- [ ] **Step 1: 在 morning.py 中集成天气 + 每日一句 + 播客**
- [ ] **Step 2: 更新飞书卡片模板，包含所有模块**
- [ ] **Step 3: 端到端测试**
- [ ] **Step 4: Commit**

---

## P3: 午报 — GPT 生成内容

### Task 13: GPT 内容生成器

**Files:**
- Create: `src/processors/llm_generator.py`

- [ ] **Step 1: 实现 llm_generator.py**

```python
def generate_tip(topic_type: str, history: list[str]) -> dict:
    """
    输入：主题类型 ("ai_tip" | "psychology" | "brand_insight") + 历史主题列表
    输出：{content: "短文", link: "延伸阅读链接", topic: "主题关键词"}
    """
```

- [ ] **Step 2: Commit**

---

### Task 14: 午报主流程

**Files:**
- Create: `src/afternoon.py`
- Create: `templates/afternoon_card.json`

- [ ] **Step 1: 实现 afternoon.py**
- [ ] **Step 2: 创建午报飞书卡片模板**
- [ ] **Step 3: 端到端测试**
- [ ] **Step 4: Commit**

---

## P4: 去重 + 卡片美化

### Task 15: 去重机制

**Files:**
- Create: `src/utils/dedup.py`
- Create: `data/seen_articles.json`

- [ ] **Step 1: 实现 dedup.py**

URL SHA256 hash 存储，7 天自动清理。

- [ ] **Step 2: 集成到 morning.py 选稿流程**
- [ ] **Step 3: Commit**

---

### Task 16: 飞书卡片美化

- [ ] **Step 1: 优化早报卡片样式（分栏、颜色、图标）**
- [ ] **Step 2: 优化午报卡片样式**
- [ ] **Step 3: Commit**

---

## P5: GitHub Actions + 开源发布

### Task 17: GitHub Actions 工作流

**Files:**
- Create: `.github/workflows/morning.yaml`
- Create: `.github/workflows/afternoon.yaml`

- [ ] **Step 1: 创建 morning.yaml（UTC 00:00 = CST 08:00）**
- [ ] **Step 2: 创建 afternoon.yaml（UTC 04:00 = CST 12:00）**
- [ ] **Step 3: Commit**

---

### Task 18: README + 开源文档

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `config.example.yaml`

- [ ] **Step 1: 写 README（中文，含截图占位）**
- [ ] **Step 2: 添加 MIT LICENSE**
- [ ] **Step 3: Commit + Tag v0.1.0**
