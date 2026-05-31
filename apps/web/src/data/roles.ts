export type UserRoleCode =
  | 'admin'
  | 'product_owner'
  | 'rd_owner'
  | 'reviewer'
  | 'knowledge_owner'
  | 'viewer';

export type UserRoleOption = {
  description: string;
  label: string;
  permissions: string[];
  value: UserRoleCode;
};

export const USER_ROLE_OPTIONS: UserRoleOption[] = [
  {
    description: '负责用户、角色、模型网关、审计与系统级配置管理。',
    label: '系统管理员',
    permissions: ['system.users.manage', 'system.model_gateway.manage', 'audit.read', 'workspace.read', 'workspace.write'],
    value: 'admin',
  },
  {
    description: '负责产品配置、版本模块、需求审批、任务生成和产品侧交付闭环。',
    label: '产品负责人',
    permissions: ['product.manage', 'requirement.approve', 'requirement.task_generate', 'bug.manage', 'workspace.read'],
    value: 'product_owner',
  },
  {
    description: '负责研发任务执行、技术方案确认、Bug 处理和研发知识沉淀。',
    label: '研发负责人',
    permissions: ['task.execute', 'review.decide', 'knowledge.manage', 'bug.manage', 'workspace.read'],
    value: 'rd_owner',
  },
  {
    description: '负责高影响 AI 输出、需求分析、设计方案和代码评审的人工确认。',
    label: '评审负责人',
    permissions: ['review.decide', 'task.read', 'workspace.read'],
    value: 'reviewer',
  },
  {
    description: '负责知识文档导入、权限角色维护、检索治理和沉淀审核。',
    label: '知识负责人',
    permissions: ['knowledge.manage', 'knowledge.search', 'workspace.read'],
    value: 'knowledge_owner',
  },
  {
    description: '只能查看有权限访问的工作台数据、任务结果、知识和看板摘要。',
    label: '查看者',
    permissions: ['workspace.read'],
    value: 'viewer',
  },
];

const USER_ROLE_LABELS = Object.fromEntries(
  USER_ROLE_OPTIONS.map((option) => [option.value, option.label]),
) as Record<string, string>;

export function formatUserRoles(roles: string[] | undefined): string {
  if (!roles?.length) {
    return '-';
  }
  return roles.map((role) => USER_ROLE_LABELS[role] ?? role).join(', ');
}
