export type ProductRecord = {
  code: string;
  id: string;
  moduleCount: number;
  name: string;
  ownerTeam: string;
  status: 'active' | 'inactive';
  version: string;
};

export type RequirementRecord = {
  content?: string;
  id: string;
  moduleCode?: string;
  owner: string;
  priority: 'P0' | 'P1' | 'P2';
  product: string;
  productId?: string;
  status: 'approved' | 'closed' | 'draft' | 'pending_approval' | 'rejected' | 'task_created';
  title: string;
  updatedAt: string;
  versionId?: string;
};

export type BugRecord = {
  assignee: string;
  description?: string;
  id: string;
  module: string;
  productId?: string;
  severity: 'blocker' | 'critical' | 'major' | 'minor';
  source: 'ai_auto_test' | 'manual_test';
  status:
    | 'assigned'
    | 'closed'
    | 'fixed'
    | 'needs_info'
    | 'open'
    | 'reopened'
    | 'triaged'
    | 'verified';
  title: string;
  versionId?: string;
};

export type KnowledgeRecord = {
  content?: string;
  documentType: string;
  id: string;
  ownerRole: string;
  permissionRoles?: string[];
  status: 'failed' | 'indexed' | 'pending_index' | 'review_pending';
  tags?: string[];
  title: string;
  updatedAt: string;
};

export type AuditRecord = {
  actor: string;
  eventType: string;
  id: string;
  result: 'success' | 'failed';
  subject: string;
  timestamp: string;
};

export type UserRecord = {
  displayName: string;
  id: string;
  roles: string[];
  rolesText: string;
  status: 'active' | 'inactive';
  username: string;
};

export const productRows: ProductRecord[] = [
  {
    code: 'AI-BRAIN',
    id: 'sample_product_ai_brain',
    moduleCount: 9,
    name: '企业 AI 大脑平台',
    ownerTeam: 'AI Platform',
    status: 'active',
    version: 'v1 MVP',
  },
  {
    code: 'RD-BRAIN',
    id: 'sample_product_rd_brain',
    moduleCount: 6,
    name: '研发大脑',
    ownerTeam: 'R&D Enablement',
    status: 'active',
    version: 'MVP-C',
  },
  {
    code: 'OPS-BRAIN',
    id: 'sample_product_ops_brain',
    moduleCount: 3,
    name: 'IT 运营大脑',
    ownerTeam: 'IT Operations',
    status: 'inactive',
    version: 'v1.1',
  },
];

export const requirementRows: RequirementRecord[] = [
  {
    content: '产品详细设计辅助',
    id: 'REQ-20260530-001',
    owner: '产品负责人',
    priority: 'P1',
    product: 'AI-BRAIN',
    status: 'task_created',
    title: '产品详细设计辅助',
    updatedAt: '2026-05-30',
  },
  {
    content: '内部 GitLab MR Code Review',
    id: 'REQ-20260530-002',
    owner: '研发负责人',
    priority: 'P0',
    product: 'RD-BRAIN',
    status: 'approved',
    title: '内部 GitLab MR Code Review',
    updatedAt: '2026-05-30',
  },
  {
    content: '知识沉淀候选审核',
    id: 'REQ-20260529-008',
    owner: '业务接口人',
    priority: 'P2',
    product: 'AI-BRAIN',
    status: 'pending_approval',
    title: '知识沉淀候选审核',
    updatedAt: '2026-05-29',
  },
];

export const bugRows: BugRecord[] = [
  {
    assignee: '前端负责人',
    id: 'BUG-001',
    module: '认证',
    severity: 'major',
    source: 'manual_test',
    status: 'open',
    title: '登录态过期提示异常',
  },
  {
    assignee: 'AI Workflow',
    id: 'BUG-002',
    module: '任务中心',
    severity: 'blocker',
    source: 'ai_auto_test',
    status: 'triaged',
    title: '人工确认后任务状态未刷新',
  },
  {
    assignee: '知识治理',
    id: 'BUG-003',
    module: '知识中心',
    severity: 'minor',
    source: 'manual_test',
    status: 'closed',
    title: '沉淀候选列表筛选项缺省',
  },
];

export const knowledgeRows: KnowledgeRecord[] = [
  {
    documentType: 'PRD',
    id: 'DOC-001',
    ownerRole: 'product_owner',
    status: 'indexed',
    title: 'AI Brain v1 产品需求文档',
    updatedAt: '2026-05-30',
  },
  {
    documentType: 'Spec',
    id: 'DOC-002',
    ownerRole: 'rd_owner',
    status: 'pending_index',
    title: '研发大脑技术规格',
    updatedAt: '2026-05-30',
  },
  {
    documentType: 'Deposit',
    id: 'DEP-003',
    ownerRole: 'knowledge_admin',
    status: 'review_pending',
    title: '产品详细设计沉淀候选',
    updatedAt: '2026-05-29',
  },
];

export const auditRows: AuditRecord[] = [
  {
    actor: 'admin@example.com',
    eventType: 'requirement.approved',
    id: 'AUD-001',
    result: 'success',
    subject: 'REQ-20260530-001',
    timestamp: '2026-05-30 11:40',
  },
  {
    actor: 'ai_task_runner',
    eventType: 'ai_task.waiting_review',
    id: 'AUD-002',
    result: 'success',
    subject: 'task_001',
    timestamp: '2026-05-30 11:42',
  },
  {
    actor: 'model_gateway',
    eventType: 'model.call',
    id: 'AUD-003',
    result: 'success',
    subject: 'local_fallback',
    timestamp: '2026-05-30 11:43',
  },
];

export const userRows: UserRecord[] = [
  {
    displayName: 'AI Brain Admin',
    id: 'user_admin',
    roles: ['admin'],
    rolesText: 'admin',
    status: 'active',
    username: 'admin@example.com',
  },
  {
    displayName: 'AI Brain Reviewer',
    id: 'user_reviewer',
    roles: ['reviewer'],
    rolesText: 'reviewer',
    status: 'active',
    username: 'reviewer@example.com',
  },
];
