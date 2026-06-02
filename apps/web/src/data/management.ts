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

export type ProductVersionRecord = {
  code: string;
  id: string;
  name: string;
  releaseDate?: string;
  startDate?: string;
  status: 'active' | 'archived' | 'planning';
};

export type ProductModuleRecord = {
  code: string;
  id: string;
  name: string;
  ownerTeam: string;
  status: 'active' | 'inactive';
};

export type ProductGitRepositoryRecord = {
  credentialRefConfigured: boolean;
  credentialStatus: string;
  defaultBranch: string;
  id: string;
  name: string;
  projectId?: string | null;
  projectPath?: string | null;
  provider: string;
  remoteUrl: string;
  repoType: string;
  rootPath: string;
  status: 'active' | 'inactive';
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
  duplicateOfBugId?: string;
  evidence?: Record<string, unknown>;
  id: string;
  module: string;
  productId?: string;
  relatedTaskId?: string;
  reproduceSteps?: string[];
  requirementId?: string;
  severity: 'blocker' | 'critical' | 'major' | 'minor';
  source: 'ai_auto_test' | 'ai_post_release' | 'manual_test';
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
  indexError?: string | null;
  ownerRole: string;
  permissionRoles?: string[];
  status: 'archived' | 'importing' | 'indexed' | 'index_failed' | 'pending_index';
  tags?: string[];
  title: string;
  updatedAt: string;
};

export type AuditRecord = {
  actor: string;
  aiTaskId?: string;
  eventType: string;
  id: string;
  payload?: Record<string, unknown>;
  result: 'success' | 'failed';
  subject: string;
  subjectId?: string;
  subjectType?: string;
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
