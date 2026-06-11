# 知识管理升级设计

---
**版本信息**

| 项目 | 值 |
|------|------|
| 功能版本 | v1.2-draft |
| 适用系统版本 | >= v1.1 |
| 文档状态 | Draft |
| 最后更新 | 2026-06-11 |

## 背景

当前知识中心已经支持知识文档导入、文本 chunk 重建、Embedding 可用时的向量索引、权限过滤检索、索引失败重试和知识沉淀审核。现有数据库已引入 `knowledge_spaces`、`knowledge_space_products`、`knowledge_space_members`、`knowledge_folders`、`knowledge_assets`、`knowledge_import_jobs` 和 `knowledge_chunk_sets`，页面已支持空间/目录筛选、文件上传、文档资产查看和导入任务查看；后续仍需继续完善目录移动、解析版本回滚、异步任务编排和检索质量评估。

后续知识管理升级应吸收 KnowFlow 的生产级知识库经验，但不直接复制 KnowFlow/RAGFlow 的运行架构。KnowFlow 可参考的方向包括：文档解析任务化、多解析器适配、OCR/转换服务解耦、图文结构保留、父子分块、权限隔离和导入治理。AI Brain 的事实源仍保持 PostgreSQL，MinIO 作为 S3-compatible 对象存储实现，承载原始文件和解析产物。

## 设计目标

1. 以知识空间作为权限和业务边界，支持按产品、部门、成员和空间角色治理知识。
2. 以目录作为空间内的信息架构，支持知识负责人整理文档，而不是只靠标签和列表筛选。
3. 以文档作为业务元数据主体，继续承载标题、类型、产品版本、权限、索引状态、标签和审计。
4. 以 MinIO 存储原始文件和解析产物，PostgreSQL 继续保存对象元数据、文档状态、chunk、embedding、权限和审计。
5. 以导入任务承载上传、转换、解析、分块、向量化、失败重试和进度展示。
6. 先兼容当前文本导入和检索能力，再分阶段引入复杂 OCR、多模态产物和父子分块。

## 非目标

1. 不把 MinIO 作为业务数据库、权限系统或检索索引。
2. 不把 KnowFlow/RAGFlow 作为 AI Brain 知识模块的强依赖。
3. 不直接复制 AGPL 项目代码；如后续需要引入任何 KnowFlow 代码或服务，必须先完成许可证和部署边界评审。
4. 不在第一阶段实现完整 OCR、版面恢复、知识质量评测和多模态检索。
5. 不绕过现有 `model_gateway` 直接调用 Embedding 或大模型 provider。

## 目标模型

```text
Knowledge Space
  -> Folder
     -> Document
        -> Asset, stored in MinIO or another S3-compatible backend
        -> Chunk Set
           -> Chunk
              -> Embedding
```

### 知识空间

知识空间是权限和业务边界。空间可以绑定部门、产品和成员，空间成员角色建议从 `reader`、`contributor`、`maintainer`、`admin` 起步。

空间规则：

1. 用户必须拥有空间读权限，才能看到空间内目录、文档、资产、chunk 和检索结果。
2. 空间写权限控制目录维护、文档上传、重解析、归档和删除。
3. `permission_roles` 保留为历史兼容字段，目标态以空间授权和用户有效权限为准。
4. 检索必须先在数据库查询层过滤用户可读空间，再进入关键词或向量召回。

### 目录

目录是空间内的信息组织层，不单独承担安全边界。目录用于承载企业知识结构，例如：

```text
支付知识空间
  -> 产品资料
  -> 技术方案
  -> 故障手册
  -> 发布复盘
  -> 客户问题
```

目录规则：

1. 目录必须归属一个知识空间。
2. 目录支持树形结构、排序、移动、重命名和归档。
3. 文档必须属于一个空间，可以不属于目录；无目录文档展示在空间根目录。
4. 目录权限默认继承空间权限，不在 v1.2 引入目录级 ACL，避免权限模型过早复杂化。

### 文档

文档继续是知识管理的业务主体。文档负责描述知识的业务含义和索引状态，不直接保存大文件。

文档目标字段：

| 字段 | 说明 |
|------|------|
| `knowledge_space_id` | 所属知识空间，目标态新文档必填。 |
| `folder_id` | 所属目录，可为空。 |
| `source_asset_id` | 原始文件资产，可为空以兼容手工文本导入。 |
| `parsed_asset_id` | 当前解析文本或 Markdown 产物。 |
| `active_chunk_set_id` | 当前生效分块版本。 |
| `parser_engine` | 当前解析器，例如 `manual_text`、`markdown`、`pdf_text`、`mineru`。 |
| `chunk_strategy` | 当前分块策略，例如 `simple_text`、`title`、`regex`、`parent_child`。 |
| `document_version` | 文档版本号，用于重上传和重解析。 |

### 资产

资产是 MinIO 对象的数据库元数据投影。所有文件访问必须先通过 API 鉴权，不能暴露长期公开 URL。

建议新增 `knowledge_assets`：

| 字段 | 说明 |
|------|------|
| `id` | 资产 ID。 |
| `knowledge_space_id` | 冗余空间 ID，便于权限过滤和清理。 |
| `document_id` | 关联文档，可为空以支持导入前暂存。 |
| `asset_type` | `original`、`converted_pdf`、`parsed_markdown`、`ocr_json`、`image`、`table`、`export_bundle`。 |
| `storage_provider` | `minio`、`s3` 或测试实现。 |
| `bucket` | 对象桶。 |
| `object_key` | 不可变对象 key。 |
| `content_hash` | 内容 hash，用于去重、校验和幂等。 |
| `mime_type` | 媒体类型。 |
| `size_bytes` | 文件大小。 |
| `metadata` | 页码、图片尺寸、解析器版本、来源 URL 等。 |
| `created_by` | 上传或生成者。 |

对象 key 使用不可变路径，例如：

```text
knowledge/{space_id}/{document_id}/{document_version}/{asset_type}/{content_hash}
```

删除文档时先标记数据库状态，再异步清理对象。对象清理失败不得让已授权用户继续通过业务入口访问已归档文档。

### 导入任务

建议新增 `knowledge_import_jobs` 管理文档处理生命周期。

状态流：

```text
uploaded -> converting -> parsing -> chunking -> embedding -> completed
                                      -> failed
                                      -> cancelled
```

任务记录应包含 `document_id`、`source_asset_id`、`parser_engine`、`chunk_strategy`、`status`、`progress`、`error_code`、`error_message`、`started_at`、`finished_at` 和 `created_by`。

### 分块版本

建议新增 `knowledge_chunk_sets` 管理一次解析和分块的版本。文档通过 `active_chunk_set_id` 指向当前生效版本，重解析先生成新的 chunk set，成功后再切换 active 指针。

`knowledge_chunk_sets` 至少包含 `document_id`、`source_asset_id`、`parsed_asset_id`、`parser_engine`、`parser_version`、`chunk_strategy`、`embedding_model`、`embedding_dimension`、`status`、`created_by`、`created_at` 和 `activated_at`。

分块版本规则：

1. 检索只使用文档当前 active chunk set 下的 chunk。
2. 新 chunk set 构建失败不得删除旧 active chunk。
3. 重解析成功后再归档旧 chunk set，保留必要审计和回滚依据。
4. 父子分块时，父块和子块必须属于同一个 chunk set。

## 处理流程

### 上传导入

1. API 校验用户对目标空间的写权限。
2. 后端把原始文件写入 MinIO，并创建 `knowledge_assets`。
3. 后端创建 `knowledge_documents` 和 `knowledge_import_jobs`。
4. 导入任务读取原始资产，执行格式转换和解析。
5. 解析后的 Markdown、OCR JSON、图片或表格资产写回 MinIO。
6. 分块结果写入新的 `knowledge_chunk_sets` 和 `knowledge_chunks`，Embedding 通过 `model_gateway` 生成。
7. 分块和索引完成后切换文档 `active_chunk_set_id`。
8. 文档进入 `text_indexed` 或 `vector_indexed`；失败时进入 `index_failed` 并记录错误，旧 active chunk set 保持可用。

### 手工文本导入

当前 `POST /api/knowledge/documents` 保留。手工文本文档可以没有 `source_asset_id`，但仍必须归属知识空间。其内容可作为 `parsed_markdown` 资产补写到对象存储，以便统一预览和版本管理。

### 检索

检索顺序必须是：

1. 解析当前用户可读知识空间。
2. 在 SQL/repository 层过滤可读文档、active chunk set 和 chunk。
3. 对兼容 embedding 配置的 chunk 执行向量召回。
4. 对文本可用 chunk 执行关键词兜底。
5. 返回结果时带上文档、目录、空间、chunk、资产引用、页码或标题层级。

父子分块启用后，子块用于召回，父块用于上下文补全；最终返回必须标明命中的子块和补全的父块来源。

## API 规划

第一阶段新增：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/knowledge/spaces` | 查询当前用户可见知识空间。 |
| `POST` | `/api/knowledge/spaces` | 创建知识空间。 |
| `PATCH` | `/api/knowledge/spaces/{space_id}` | 更新空间元数据。 |
| `PUT` | `/api/knowledge/spaces/{space_id}/members` | 维护空间成员。 |
| `GET` | `/api/knowledge/spaces/{space_id}/folders` | 查询空间目录树。 |
| `POST` | `/api/knowledge/spaces/{space_id}/folders` | 创建目录。 |
| `PATCH` | `/api/knowledge/folders/{folder_id}` | 重命名、移动、归档目录。 |
| `POST` | `/api/knowledge/documents/upload` | 上传文件并创建导入任务。 |
| `GET` | `/api/knowledge/documents/{document_id}/assets` | 查询文档资产。 |
| `GET` | `/api/knowledge/assets/{asset_id}/preview` | 鉴权后返回预览或短期签名 URL。 |
| `GET` | `/api/knowledge/import-jobs` | 查询导入任务。 |
| `POST` | `/api/knowledge/import-jobs/{job_id}/retry` | 重试导入任务。 |

兼容接口：

1. `GET /api/knowledge/documents` 增加 `knowledge_space_id`、`folder_id`、`asset_type` 和 `import_status` 筛选。
2. `POST /api/knowledge/documents` 保留手工文本导入，但目标态要求 `knowledge_space_id`。
3. `PATCH /api/knowledge/documents/{document_id}` 支持移动目录、更新解析策略和触发重索引。
4. `POST /api/knowledge/search` 增加空间范围、目录范围和父子分块返回字段。

## 前端规划

知识中心目标布局：

1. 左侧空间与目录树：空间切换、目录新增、移动、归档。
2. 中部文档列表：按目录、类型、索引状态、导入状态、产品版本、标签筛选。
3. 右侧或抽屉详情：文档元数据、资产列表、解析预览、chunk 预览、导入任务时间线。
4. 上传导入弹窗：目标空间、目录、产品、版本、权限继承、文件、解析器、分块策略。
5. 检索弹窗：选择空间范围，展示命中 chunk、父块上下文、来源目录、页码和资产预览入口。
6. 沉淀审核：采纳时选择空间和目录，避免任务沉淀继续进入无组织的文档池。

## 分阶段实施

### Phase 1: 空间目录与 MinIO 基础

交付：

1. 对象存储配置、健康检查和 `ObjectStoragePort`。
2. MinIO Docker Compose 服务和私有 bucket 初始化。
3. `knowledge_assets`、`knowledge_folders`、文档空间/目录字段迁移。
4. 文档上传 API、资产查询 API 和鉴权下载/预览 API。
5. 前端空间选择、目录树、文件上传和资产列表。

验收重点：

1. 新文档必须归属知识空间。
2. 用户看不到未授权空间内文档、资产和检索结果。
3. MinIO 对象不能通过长期公开 URL 访问。
4. 手工文本导入兼容旧流程。

### Phase 2: 导入任务与解析产物

交付：

1. `knowledge_import_jobs`。
2. txt、md、pdf 基础文本解析。
3. 解析 Markdown 资产写入 MinIO。
4. 导入进度、失败原因、重试和 chunk 预览。

验收重点：

1. 解析失败不丢原始文件。
2. 重试不会重复创建同一文档或重复暴露旧 chunk。
3. Embedding 不可用时仍可进入 `text_indexed`。

### Phase 3: KnowFlow 风格解析增强

交付：

1. Parser adapter 接口。
2. Gotenberg、MinerU、PaddleOCR、DOTS 等外部解析器适配位。
3. 标题分块、正则分块、父子分块。
4. 图片、表格、页码和标题层级来源引用。

验收重点：

1. 解析器失败可降级或给出明确失败状态。
2. 父子分块结果可解释，检索结果能回溯到原文位置。
3. 不引入未经评审的外部许可证代码。

### Phase 4: 知识质量与运营

交付：

1. 知识质量指标：解析失败率、索引失败率、无答案率、低命中率、重复文档。
2. 评测集和检索回归。
3. 知识治理队列：待补充、待归档、待重解析、低质量 chunk。

验收重点：

1. 能解释为什么某个问题没有命中知识。
2. 知识负责人能持续治理空间，而不是只处理一次性导入。

## 安全与审计

1. 所有空间、目录、文档、资产、chunk、导入任务读取都必须校验用户有效权限。
2. 下载、预览、上传、删除、移动目录、重解析、权限变更和沉淀采纳必须写入审计。
3. 对象存储 bucket 默认为私有，不允许公开读。
4. 预签名 URL 必须短期有效，并且只能在 API 鉴权通过后生成。
5. 模型日志仍只记录 provider、model、purpose、tokens、latency、status、error 和配置 id，不记录完整 prompt、完整输出或密钥。

## 设计 Review

| 评审项 | 发现 | 优化结论 |
|--------|------|----------|
| 架构边界 | 直接复制 KnowFlow/RAGFlow 会冲击 AI Brain 模块化单体和 DB-first 事实源。 | 只吸收解析器、导入任务、父子分块和治理思路；不引入 RAGFlow 作为知识底座。 |
| 存储一致性 | MinIO 对象和 PostgreSQL 元数据可能出现半成功。 | PostgreSQL 作为业务事实源；对象 key 不可变；删除和清理采用数据库状态优先、异步清理对象。 |
| 权限泄露 | 对象存储 URL 可能绕过知识权限。 | 所有访问先走 API 鉴权；只返回短期签名 URL 或代理流；检索前先做 SQL 权限过滤。 |
| 范围过大 | OCR、多模态、父子分块和质量评测一次性交付风险高。 | 分四期实施，Phase 1 只落空间目录、MinIO 基础和兼容上传。 |
| 兼容迁移 | 现有文档缺少 `knowledge_space_id`。 | 提供默认迁移空间和兼容 `permission_roles`，新文档逐步强制空间归属。 |
| 用户体验 | 仅增加上传会把知识中心变成文件仓库。 | 前端以空间目录树、文档列表、资产预览、chunk 预览和导入任务共同组织。 |

## 待实施前确认

1. 默认迁移空间命名建议为 `rd_brain_default`，用于承接历史知识文档。
2. 目录级 ACL 暂不进入 v1.2，除非真实组织场景证明空间级权限不够。
3. Phase 1 是否必须支持 PDF 内容抽取，可在实施计划中按交付窗口决定；即便暂不抽取，也应先支持原始 PDF 资产存储和权限预览。
4. MinIO 作为本地和私有化默认对象存储，接口层保持 S3-compatible 抽象，避免后续迁移到云厂商 S3 时重写知识业务逻辑。
