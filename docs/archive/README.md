# Archive

这里保存项目早期设计稿和实现计划。

这些文档已经过时，仅供追溯历史，不应作为当前部署指南。当前版本请参考仓库根目录的 `README.md`、`config/config.example.yaml` 和 `.env.example`。

主要过时点：

- 当前默认使用飞书自建应用私聊推送，不是飞书 webhook。
- 当前推荐 cron-job.org 触发 GitHub `repository_dispatch`，不是 GitHub Actions cron。
- 当前使用 OpenAI 兼容接口配置 `OPENAI_BASE_URL`，模型名以 `config.example.yaml` 为准。
- 当前播客推荐来自 Apple Podcasts 热榜，不是小宇宙固定 RSS。
- 当前运行数据 `data/*.json` 不再提交到 Git。
