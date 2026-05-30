# 快速入门

## 适用人群

需要本地启动、验证或继续实现 AI Brain 的开发者、测试人员和 AI 编码助手。

## 前置知识

- 熟悉 Docker Compose 基本命令。
- 了解 React、FastAPI、PostgreSQL、Redis 的基本用途。
- 阅读 [AI Brain 文档中心](../README.md)、[项目级 PRD](../01-prd/enterprise-ai-brain/prd.md) 和 [项目级技术规格](../02-specs/enterprise-ai-brain/spec.md)。

## 当前源码状态提示

当前仓库已包含 `apps/api` FastAPI 后端、`apps/web` Ant Design Pro 工作台、`.env.example`、`docker-compose.yml` 和 PostgreSQL 初始化迁移脚本。当前后端请求处理仍使用进程内 `MemoryStore` 支撑本地测试和演示；迁移脚本定义的是目标持久化 schema，后续接入数据库仓储时应继续以项目级 PRD/spec/API/test-case 为准。

## 环境准备

### 必需软件

| 软件 | 版本 | 安装方式 |
|------|------|----------|
| Docker Desktop / Docker Engine | 支持 Compose v2 | 按操作系统安装。 |
| Git | 任意维护版本 | 按操作系统安装。 |

### 可选软件

| 软件 | 用途 |
|------|------|
| uv | 本地运行 FastAPI 测试和依赖管理。 |
| Node.js | 本地运行 React 开发服务。 |

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/zeek428/e-ai-brain.git
cd e-ai-brain
```

### 2. 配置环境

```bash
cp .env.example .env
```

根据本地模型网关和数据库配置编辑 `.env`。首次安装依赖需要网络访问；如本机依赖安装受限，优先使用 Docker Compose。

本地种子账号只用于本地验证，非本地环境会默认禁用。前端工作台不会内置或自动提交 admin 密码；需要真实 API 数据时，先通过登录接口获取 token，再写入浏览器 `localStorage.ai_brain_access_token`。

### 3. 校验 Compose 配置

```bash
docker compose config
```

### 4. 启动服务

```bash
docker compose up -d --build
```

### 5. 验证安装

```bash
curl http://localhost:8000/health
```

预期 API 返回健康状态。默认端口为：API `8000`、Web `5173`、PostgreSQL `5432`、Redis `6379`。

## 常见问题

| 错误信息 | 原因 | 解决方案 |
|----------|------|----------|
| dependency install failed | 首次依赖安装需要网络 | 使用 Docker Compose 或配置可用镜像源。 |
| database connection failed | PostgreSQL 未启动或环境变量不一致 | 检查 `.env` 与 compose 服务名。 |
| pgvector extension missing | 数据库初始化未执行 | 检查迁移脚本和 postgres 镜像扩展支持。 |

## 下一步

- 阅读 [系统架构](../02-specs/architecture/system-overview.md)。
- 阅读 [项目级 PRD](../01-prd/enterprise-ai-brain/prd.md)。
- 阅读 [项目级技术规格](../02-specs/enterprise-ai-brain/spec.md)。
- 运行 [测试用例](../02-specs/enterprise-ai-brain/test-case.md) 对应验证。

## 获取帮助

- 文档问题: 更新 [docs/](../) 下对应文件。
- 需求、技术、接口或测试问题: 先查看项目级 PRD/spec/API/test-case。

---
最后更新: 2026-05-29
