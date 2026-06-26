# TradingAgents 中文增强+二次开发版

**🎯 我们的定位与使命**: 专注学习与研究，提供中文化学习中心与工具，合规友好，支持 A股/港股/美股 的分析与教学，推动 AI 金融技术在中文社区的普及与正确使用。

## 🎉 v1.0.1 版本说明 - 配置体验与同步稳定性增强

> 🚀 **当前推荐版本**: `v1.0.1` 已正式可用，在 `v1.0.0-preview` 架构基础上，重点增强配置管理、聚合厂家、页面切换、单股同步和上游能力吸收。

### ✨ 核心特性

#### 🏗️ **全新技术架构**

- **后端升级**: 从 Streamlit 迁移到 FastAPI，提供更强大的 RESTful API
- **前端重构**: 采用 Vue 3 + Element Plus，打造现代化的单页应用
- **数据库优化**: MongoDB + Redis 双数据库架构，性能提升 10 倍
- **容器化部署**: 完整的 Docker 多架构支持（amd64 + arm64）

#### 🚀 **v1.0.1 重点增强**

- **配置管理优化**: 新增厂家、模型目录和大模型配置支持按最新添加顺序置顶显示
- **聚合厂家增强**: 新增 `AiHubMix` 聚合 LLM 厂家，并支持聚合渠道初始化能力
- **模型选择统一排序**: 配置页、对话框和分析页中的模型列表顺序保持一致
- **页面切换修复**: 股票详情页和报告详情页切换后会自动刷新正确内容
- **单股同步增强**: 同步结果支持展示主链路、回退链路、失败原因和 `market_quotes` 落库状态
- **AKShare 兜底增强**: 单股实时行情支持 `stock_bid_ask_em -> stock_zh_a_spot -> stock_zh_a_spot_em -> stock_zh_a_hist` 多级降级链
- **上游能力同步**: 同步 `llm_clients`、共享模型目录、provider 规范键、图层初始化路径和数据库迁移增强等能力

#### 🎯 **企业级功能**

- **用户权限管理**: 完整的用户认证、角色管理、操作日志系统
- **配置管理中心**: 可视化的大模型配置、数据源管理、系统设置
- **缓存管理系统**: 智能缓存策略，支持 MongoDB/Redis/文件多级缓存
- **实时通知系统**: SSE+WebSocket 双通道推送，实时跟踪分析进度和系统状态
- **批量分析功能**: 支持多只股票同时分析，提升工作效率
- **智能股票筛选**: 基于多维度指标的股票筛选和排序系统
- **自选股管理**: 个人自选股收藏、分组管理和跟踪功能
- **个股详情页**: 完整的个股信息展示和历史分析记录
- **模拟交易系统**: 虚拟交易环境，验证投资策略效果

#### 🤖 **智能分析增强**

- **动态供应商管理**: 支持动态添加和配置 LLM 供应商
- **模型能力管理**: 智能模型选择，根据任务自动匹配最佳模型
- **多数据源同步**: 统一的数据源管理，支持 Tushare、AkShare、BaoStock
- **报告导出功能**: 支持 Markdown/Word/PDF 多格式专业报告导出

#### 🔧 **重大Bug修复**

- **技术指标计算修复**: 彻底解决市场分析师技术指标计算不准确问题
- **基本面数据修复**: 修复基本面分析师PE、PB等关键财务数据计算错误
- **死循环问题修复**: 解决部分用户在分析过程中触发的无限循环问题
- **数据一致性优化**: 确保所有分析师使用统一、准确的数据源

#### 🐳 **Docker 多架构支持**

- **跨平台部署**: 支持 x86_64 和 ARM64 架构（Apple Silicon、树莓派、AWS Graviton）
- **GitHub Actions**: 自动化构建和发布 Docker 镜像
- **一键部署**: 完整的 Docker Compose 配置，5 分钟快速启动

### 📊 技术栈升级

| 组件               | v0.1.x       | v1.0.1                         |
| ------------------ | ------------ | ------------------------------ |
| **后端框架** | Streamlit    | FastAPI + Uvicorn              |
| **前端框架** | Streamlit    | Vue 3 + Vite + Element Plus    |
| **数据库**   | 可选 MongoDB | MongoDB + Redis                |
| **API 架构** | 单体应用     | RESTful API + WebSocket        |
| **部署方式** | 本地/Docker  | Docker 多架构 + GitHub Actions |

#### 📥 安装部署

**两种部署方式，任选其一**：

| 部署方式               | 适用场景         | 难度        | 文档链接                                                          |
| ---------------------- | ---------------- | ----------- | ----------------------------------------------------------------- |
| 🐳**Docker版**   | 生产环境、跨平台 | ⭐⭐ 中等   | [Docker 部署指南](https://mp.weixin.qq.com/s/JkA0cOu8xJnoY_3LC5oXNw) |
| 💻**本地代码版** | 开发者、定制需求 | ⭐⭐⭐ 较难 | [本地安装指南](https://mp.weixin.qq.com/s/cqUGf-sAzcBV19gdI4sYfA)    |

⚠️ **重要提醒**：在分析股票之前，请按相关文档要求，将股票数据同步完成，否则分析结果将会出现数据错误。

#### 📚 使用指南

在使用前，建议先阅读详细的使用指南：

- **[v1.0.1 发布说明](./docs/releases/v1.0.1-release-notes.md)**
- **[v1.0.1 使用手册](./docs/guides/v1.0.1-user-manual.md)**
- **[v1.0.1 升级指南](./docs/releases/upgrade-guide.md)**
- **[完整更新日志](./docs/releases/CHANGELOG.md)**
- **[0、📘 TradingAgents-CN v1.0.0-preview 快速入门视频](https://www.bilibili.com/video/BV1i2CeBwEP7/?vd_source=5d790a5b8d2f46d2c10fd4e770be1594)**
- **[1、📘 TradingAgents-CN v1.0.0-preview 使用指南](https://mp.weixin.qq.com/s/ppsYiBncynxlsfKFG8uEbw)**
- **[2、📘 使用 Docker Compose 部署TradingAgents-CN v1.0.0-preview（完全版）](https://mp.weixin.qq.com/s/JkA0cOu8xJnoY_3LC5oXNw)**
- **[3、📘 从 Docker Hub 更新 TradingAgents‑CN 镜像](https://mp.weixin.qq.com/s/WKYhW8J80Watpg8K6E_dSQ)**
- **[4、📘 TradingAgents-CN v1.0.0-preview绿色版安装和升级指南](https://mp.weixin.qq.com/s/eoo_HeIGxaQZVT76LBbRJQ)**
- **[5、📘 TradingAgents-CN v1.0.0-preview绿色版端口配置说明](https://mp.weixin.qq.com/s/o5QdNuh2-iKkIHzJXCj7vQ)**
- **[6、📘 TradingAgents v1.0.0-preview 源码版安装手册（修订版）](https://mp.weixin.qq.com/s/cqUGf-sAzcBV19gdI4sYfA)**
- **[7、📘 TradingAgents v1.0.0-preview 源码安装视频教程](https://www.bilibili.com/video/BV1FxCtBHEte/?vd_source=5d790a5b8d2f46d2c10fd4e770be1594)**

使用指南包含：

- ✅ 完整的功能介绍和操作演示
- ✅ 详细的配置说明和最佳实践
- ✅ 常见问题解答和故障排除
- ✅ 实际使用案例和效果展示

### 数据库运维补充

- 数据库版本隔离、共享库保护、迁移脚本与 provider 规范化说明：
  - [数据库版本隔离与 Provider 规范化](./docs/deployment/database/DB_VERSION_ISOLATION_AND_PROVIDER_NORMALIZATION.md)

### 上游吸收补充

- 当前项目采用人工选择性吸收上游更新：

  - [上游同步策略](./docs/maintenance/upstream-sync.md)
  - [人工上游吸收清单](./docs/maintenance/manual-upstream-absorption-checklist.md)
- `v1.0.1` 已明确同步到当前版本的上游能力包括：

  - `llm_clients` 抽象层主链路
  - 共享模型目录与轻量校验
  - provider canonical key 规范化
  - `trading_graph.py` 主要 provider 初始化路径收口
  - `fundamentals_analyst.py` 中 qwen fresh llm 重建逻辑
  - 图层参数透传、工厂别名兼容、风控引用修复
  - provider 默认 URL / 环境变量映射统一
  - MongoDB 默认库名、版本隔离命名与迁移脚本增强
    ## 🆚 中文增强特色
