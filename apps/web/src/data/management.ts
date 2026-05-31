export type ProductRecord = {
  code: string;
  id: string;
  moduleCount: number;
  name: string;
  ownerTeam: string;
  status: 'active' | 'inactive';
  version: string;
};

export type ProductVersionOption = {
  code: string;
  id: string;
  name: string;
  status: string;
};

export type ProductContextOption = {
  code: string;
  id: string;
  name: string;
  versions: ProductVersionOption[];
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

export type ModelGatewayConfigRecord = {
  apiKeyConfigured: boolean;
  baseUrl: string;
  defaultChatModel: string;
  defaultEmbeddingModel: string;
  id: string;
  isDefault: boolean;
  keyStatus: string;
  maxRetries: number;
  name: string;
  provider: string;
  status: 'active' | 'inactive';
  timeoutSeconds: number;
};
