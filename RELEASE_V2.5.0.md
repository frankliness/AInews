# Phoenix v2.5.0 发布说明

## 🎉 版本信息
- **版本号**: v2.5.0
- **发布日期**: 2025年9月4日
- **版本类型**: 功能里程碑版本 (Feature Milestone)

## 🚀 主要更新

### 核心功能：集成 Gemini AI 实现选题自动化
- **新增 AI 内容创作流**: 引入 `gemini_card_generation_dag`，每日自动调用 Google Vertex AI 的 Gemini 2.5 Pro 模型，将 Phoenix 摘要加工成结构化的 Markdown 选题简报。
- **新增自动化邮件分发**: 引入 `email_distribution_dag`，每日定时将生成的选题简报以 HTML 正文和 Markdown 附件的形式，发送至指定邮箱，实现端到端的自动化交付。
- **增强的健壮性**: 对 Gemini API 调用增加了超时、重试和指数退避机制；对邮件发送和文件查找增加了详细的错误处理和报警功能。

### 技术架构优化
- **核心逻辑模块化**: 将 AI 调用和邮件发送逻辑分别封装到 `gemini_utils.py` 和 `email_utils.py` 模块中，实现了代码解耦和复用。
- **全面的可配置性**: 所有新增功能（调度时间、GCP配置、模型参数、收件人列表等）均通过 Airflow Variables 进行管理，无需修改代码即可调整。

## 📋 详细变更

### 新增文件
- `dags/phoenix/gemini_card_generation_dag.py`: 内容创作核心 DAG。
- `dags/phoenix/email_distribution_dag.py`: 邮件分发核心 DAG。
- `dags/phoenix/gemini_utils.py`: Gemini API 交互工具模块。
- `dags/phoenix/email_utils.py`: 邮件发送工具模块。
- `exports/.gitkeep`: 确保空的 `exports` 目录被 Git 追踪。
- `gemini_outputs/.gitkeep`: 确保空的 `gemini_outputs` 目录被 Git 追踪。
- `RELEASE_V2.5.0.md`: 本次发布说明。

### 修改文件
- `README.md`: 全面更新以反映新的系统架构、数据流和配置项。
- `requirements.txt`: 添加 `google-cloud-aiplatform`, `google-generativeai`, `Markdown` 等新依赖。
- `docker-compose.phoenix.yml`: 为 Airflow 服务添加了 GCP 认证环境变量和新的目录挂载。
- `docs/*.md`: 同步更新部署和使用文档。

### 删除文件
- `vertexapi_test.py`: 移除了过时的演示脚本。
- `RELEASE_V2.4.2.md`: 归档旧的发布说明。


