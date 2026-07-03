# 平台配置与模型网关 API

> API 分册。覆盖相关系统、模型网关配置、连接测试和模型调用日志。主入口见 [../api.md](../api.md)，分册组索引见 [system-governance-and-platform.md](system-governance-and-platform.md)。

### 平台配置

相关系统：

```http
GET /api/system/related-systems?active_only=true&product_id=product_rd
POST /api/system/related-systems
PATCH /api/system/related-systems/{system_id}
```

请求体：

```json
{
  "code": "knowledge",
  "name": "知识中心",
  "description": "文档导入、检索和知识沉淀",
  "owner_team": "rd",
  "product_id": "product_rd",
  "status": "active",
  "display_order": 100
}
```

模型网关配置：

```http
GET /api/system/model-gateway-configs?page=1&page_size=10&sort_by=name&sort_order=asc
POST /api/system/model-gateway-configs/test
POST /api/system/model-gateway-configs
PATCH /api/system/model-gateway-configs/{config_id}
DELETE /api/system/model-gateway-configs/{config_id}
```

`GET /api/system/model-gateway-configs` 未传 `page/page_size` 时保留原全量列表兼容响应；分页模式支持 `name`、`provider`、`status`、`is_default`、`default_chat_model`、`default_embedding_model`、`embedding_connection_mode` 筛选，支持按 `name/provider/status/is_default/base_url/default_chat_model/default_embedding_model/embedding_connection_mode/id` 排序，并返回 `query` 与 `performance` 元数据用于定位模型网关配置页查询耗时。

请求体：

```json
{
  "name": "默认模型网关",
  "provider": "openai_compatible",
  "base_url": "https://api.example.com/v1",
  "api_key": "<redacted>",
  "default_chat_model": "chat-model",
  "default_embedding_model": "embedding-model",
  "embedding_connection_mode": "reuse_chat",
  "embedding_base_url": null,
  "embedding_api_key": null,
  "embedding_dimension": 1536,
  "timeout_seconds": 60,
  "max_retries": 1,
  "status": "active",
  "is_default": true
}
```

响应不会返回明文 `api_key`、`embedding_api_key`、密钥前缀或后缀，只返回 `api_key_configured` 和 `embedding_api_key_configured`。`embedding_connection_mode` 可取 `disabled`、`reuse_chat` 或 `custom`：`disabled` 表示仅启用 Chat 能力，`reuse_chat` 使用 Chat 的 `base_url/api_key` 调用 `/embeddings`，`custom` 使用 `embedding_base_url/embedding_api_key` 调用 `/embeddings`。`default_embedding_model` 在 `disabled` 模式可为空；`embedding_dimension` 当前必须等于系统 `VECTOR_DIMENSION`。
`provider` 目前仅允许 `openai_compatible`；新增或编辑提交其他 provider 返回 `400 VALIDATION_ERROR`，不得保存为 active/default 配置。

测试检测：

```http
POST /api/system/model-gateway-configs/test
```

请求体使用模型网关配置字段，可选传入 `config_id`。编辑已有配置时，如果请求体不含 `api_key` 且 `config_id` 对应配置已保存密钥，则使用服务端已有密钥完成本次 Chat 测试；`embedding_connection_mode=custom` 且请求体不含 `embedding_api_key` 时，可复用已有配置中的服务端 Embedding 密钥。新增配置测试必须显式提交所需密钥。`test_target` 默认为 `chat_and_embedding`，可取 `chat_and_embedding`、`chat` 或 `embedding`；当 `test_target=chat` 或 `embedding_connection_mode=disabled` 时不要求 `default_embedding_model`，Embedding 段返回 `status=skipped`。

```json
{
  "config_id": "model_config_default",
  "name": "默认模型网关",
  "provider": "openai_compatible",
  "base_url": "https://api.example.com/v1",
  "api_key": "<redacted>",
  "default_chat_model": "chat-model",
  "default_embedding_model": "embedding-model",
  "embedding_connection_mode": "custom",
  "embedding_base_url": "https://embedding.example.com/v1",
  "embedding_api_key": "<redacted>",
  "embedding_dimension": 1536,
  "timeout_seconds": 60,
  "max_retries": 1,
  "status": "active",
  "is_default": true,
  "test_target": "chat_and_embedding"
}
```

成功或 provider 调用失败都返回脱敏检测结果；整体 `ok=false` 时前端应展示失败段和 `error_code`，不把本次测试自动保存为配置。

```json
{
  "ok": true,
  "chat": {
    "ok": true,
    "status": "succeeded",
    "model": "chat-model",
    "latency_ms": 18
  },
  "embedding": {
    "ok": true,
    "status": "succeeded",
    "model": "embedding-model",
    "latency_ms": 12,
    "dimension": 1536
  },
  "test_target": "chat_and_embedding"
}
```

仅测试 Chat 的响应示例：

```json
{
  "ok": true,
  "chat": {
    "ok": true,
    "status": "succeeded",
    "model": "codex-auto-review",
    "latency_ms": 18
  },
  "embedding": {
    "ok": true,
    "status": "skipped",
    "model": ""
  },
  "test_target": "chat"
}
```

测试接口会按 `test_target` 临时调用 `{base_url}/chat/completions` 和/或 Embedding 连接对应的 `/embeddings`，但不得持久化配置、密钥或写入 `model_gateway_logs`；只写入 `model_gateway_config.tested` 审计事件，载荷包含 provider、测试范围和测试状态，不包含密钥、完整 prompt 或完整输出。`test_target=chat` 只证明 Chat 能力可用，不代表知识索引、知识检索或长期记忆 embedding 能力可用。健康检查继续返回兼容字段 `model_gateway`，并额外返回 `chat_gateway` 与 `embedding_gateway`，Embedding 可为 `configured`、`disabled`、`failed` 或 `not_configured`。

模型调用日志：

```http
GET /api/model-gateway/logs?ai_task_id=task_001&status=succeeded&page=1&page_size=10&sort_by=created_at&sort_order=desc
```

模型调用日志只返回 `provider`、`model`、`purpose`、`tokens`、`latency_ms`、`status`、`error`、`created_at` 和 `model_gateway_config_id` 等元数据，不返回完整 prompt、完整模型输出或密钥。带 `page/page_size` 时返回 `page`、`page_size`、`total`、`query` 和 `performance`，PostgreSQL 运行态优先走模型日志 count/page read model；未分页请求继续兼容历史全量读取。
