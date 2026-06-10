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
  description?: string;
  id: string;
  name: string;
  status: string;
};

export type ProductVersionRecord = {
  code: string;
  description?: string;
  id: string;
  name: string;
  productCode?: string;
  productId?: string;
  productName?: string;
  releaseDate?: string;
  startDate?: string;
  status: 'active' | 'archived' | 'planning' | 'released' | 'testing';
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

export type ProductVersionBranchConfigRecord = {
  baseBranch: string;
  branchStatus: 'active' | 'archived' | 'merged' | 'not_created' | 'released' | 'testing';
  creationSource: 'ai_task' | 'github_sync' | 'gitlab_sync' | 'manual';
  description?: string | null;
  id: string;
  productId: string;
  repositoryDefaultBranch?: string | null;
  repositoryId: string;
  repositoryName?: string | null;
  repositoryPath?: string | null;
  repositoryProvider?: string | null;
  versionId: string;
  workingBranch: string;
};

export type ProductRelatedSystemRecord = {
  code: string;
  description?: string | null;
  id: string;
  name: string;
  ownerTeam: string;
  productId?: string | null;
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
  createdAt: string;
  id: string;
  moduleCode?: string;
  owner: string;
  priority: 'P0' | 'P1' | 'P2';
  product: string;
  productId?: string;
  source?: string;
  status:
    | 'accepted'
    | 'approved'
    | 'cancelled'
    | 'closed'
    | 'code_reviewing'
    | 'deferred'
    | 'designing'
    | 'developing'
    | 'draft'
    | 'planned'
    | 'ready_for_dev'
    | 'ready_for_release'
    | 'rejected'
    | 'released'
    | 'submitted'
    | 'testing';
  title: string;
  updatedAt: string;
  versionId?: string;
  versionName?: string;
};

export type BugRecord = {
  assignee: string;
  createdAt: string;
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
  versionName: string;
};

export type KnowledgeRecord = {
  activeChunkSetId?: string;
  content?: string;
  documentType: string;
  folderId?: string;
  folderPath?: string;
  id: string;
  indexError?: string | null;
  knowledgeSpaceId?: string;
  ownerRole: string;
  permissionRoles?: string[];
  sourceAssetId?: string;
  status:
    | 'archived'
    | 'importing'
    | 'indexed'
    | 'index_failed'
    | 'pending_index'
    | 'text_indexed'
    | 'vector_indexed';
  tags?: string[];
  title: string;
  updatedAt: string;
  vectorIndexError?: string | null;
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
  defaultEmbeddingModel?: string | null;
  embeddingApiKeyConfigured: boolean;
  embeddingBaseUrl?: string | null;
  embeddingConnectionMode: 'custom' | 'disabled' | 'reuse_chat';
  embeddingDimension?: number | null;
  id: string;
  isDefault: boolean;
  keyStatus: string;
  maxRetries: number;
  name: string;
  provider: string;
  status: 'active' | 'inactive';
  timeoutSeconds: number;
};
