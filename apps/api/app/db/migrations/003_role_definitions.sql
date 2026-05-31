CREATE TABLE IF NOT EXISTS role_definitions (
  code text PRIMARY KEY,
  name text NOT NULL,
  description text NOT NULL,
  permissions jsonb NOT NULL DEFAULT '[]'::jsonb,
  is_assignable boolean NOT NULL DEFAULT true,
  sort_order integer NOT NULL DEFAULT 0,
  status text NOT NULL DEFAULT 'active',
  updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO role_definitions (code, name, description, permissions, is_assignable, sort_order, status)
VALUES
  ('admin', '系统管理员', '负责用户、角色、模型网关、审计与系统级配置管理。', '["system.users.manage", "system.model_gateway.manage", "audit.read", "workspace.read", "workspace.write"]'::jsonb, true, 10, 'active'),
  ('product_owner', '产品负责人', '负责产品配置、版本模块、需求审批、任务生成和产品侧交付闭环。', '["product.manage", "requirement.approve", "requirement.task_generate", "bug.manage", "workspace.read"]'::jsonb, true, 20, 'active'),
  ('rd_owner', '研发负责人', '负责研发任务执行、技术方案确认、Bug 处理和研发知识沉淀。', '["task.execute", "review.decide", "knowledge.manage", "bug.manage", "workspace.read"]'::jsonb, true, 30, 'active'),
  ('reviewer', '评审负责人', '负责高影响 AI 输出、需求分析、设计方案和代码评审的人工确认。', '["review.decide", "task.read", "workspace.read"]'::jsonb, true, 40, 'active'),
  ('knowledge_owner', '知识负责人', '负责知识文档导入、权限角色维护、检索治理和沉淀审核。', '["knowledge.manage", "knowledge.search", "workspace.read"]'::jsonb, true, 50, 'active'),
  ('viewer', '查看者', '只能查看有权限访问的工作台数据、任务结果、知识和看板摘要。', '["workspace.read"]'::jsonb, true, 60, 'active')
ON CONFLICT (code) DO UPDATE SET
  name = EXCLUDED.name,
  description = EXCLUDED.description,
  permissions = EXCLUDED.permissions,
  is_assignable = EXCLUDED.is_assignable,
  sort_order = EXCLUDED.sort_order,
  status = EXCLUDED.status,
  updated_at = now();
