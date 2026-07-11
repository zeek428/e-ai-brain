import type { UserRecord } from '../data/management';
import { formatUserRoles, type UserRoleDefinition } from '../data/roles';
import {
  apiRequest,
  appendQueryParam,
  appendRemoteListParams,
} from './apiClient';
import type {
  ListResponse,
  RemoteListPerformance,
} from './apiClient';
import { requireAccessToken } from './authClient';
import type { ScopeGrant } from './authClient';

type RemoteSortOrder = 'ascend' | 'descend';

type RemoteListQuery = {
  page?: number;
  pageSize?: number;
  sortField?: string;
  sortOrder?: RemoteSortOrder;
};

type RemoteListResult<Row> = {
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: Row[];
  total: number;
};

export type UserListQuery = RemoteListQuery & {
  displayName?: string;
  role?: string;
  status?: string;
  username?: string;
};

export type RoleListQuery = RemoteListQuery & {
  businessRole?: string;
  category?: string;
  menuScope?: string;
  permission?: string;
  role?: string;
  status?: string;
};

export type MenuListQuery = RemoteListQuery & {
  menu?: string;
  menuType?: string;
  parent?: string;
  path?: string;
  permission?: string;
  status?: string;
};

export type PermissionRecord = {
  category?: string;
  code: string;
  description?: string;
  is_system?: boolean;
  name: string;
  risk_level?: string;
  status?: string;
};

export type MenuResourceRecord = {
  code: string;
  icon?: string;
  is_system?: boolean;
  menu_type?: string;
  name: string;
  parent_code?: string | null;
  path?: string | null;
  required_permissions?: string[];
  sort_order?: number;
  status?: string;
};

export type MenuResourceMutationPayload = {
  code?: string;
  icon?: string;
  menu_type?: string;
  name?: string;
  parent_code?: string | null;
  path?: string;
  required_permissions?: string[];
  sort_order?: number;
  status?: string;
};

export type SystemSettingsRecord = {
  admin_email?: string | null;
  admin_email_configured?: boolean;
  email_delivery?: SystemEmailDeliverySettings | null;
  email_delivery_configured?: boolean;
  test_recipient_email?: string | null;
  test_recipient_email_configured?: boolean;
  updated_at?: string | null;
  updated_by?: string | null;
};

export type SystemEmailDeliverySettings = {
  default_from?: string | null;
  enabled?: boolean;
  reply_to?: string | null;
  sender_email?: string | null;
  smtp_host?: string | null;
  smtp_password?: string | null;
  smtp_password_configured?: boolean;
  smtp_port?: number | null;
  smtp_secret_ref?: string | null;
  smtp_secret_ref_configured?: boolean;
  smtp_tls?: string | null;
  smtp_username?: string | null;
};

export type SystemSettingsMutationPayload = {
  admin_email?: string | null;
  email_delivery?: SystemEmailDeliverySettings | null;
  high_risk_confirmation?: {
    confirmed?: boolean;
    reason?: string | null;
  } | null;
  test_recipient_email?: string | null;
};

export type SystemEmailDeliveryTestPayload = {
  recipient_email?: string | null;
};

export type SystemEmailDeliveryTestResult = {
  delivery_status: string;
  message_id?: string;
  message_subject?: string;
  recipient_email: string;
  sent_at?: string;
  smtp_host: string;
  smtp_port: number;
  smtp_tls: string;
};

export type SystemHealthCheckRecord = {
  action_href?: string | null;
  category: string;
  component: string;
  description: string;
  fix_suggestion: string;
  key: string;
  last_error?: string | null;
  metrics?: Record<string, unknown>;
  status: string;
  title: string;
};

export type SystemHealthRecommendationRecord = {
  action_href?: string | null;
  component: string;
  message: string;
  severity: string;
  title: string;
};

export type SystemHealthAlertRecord = {
  action_href?: string | null;
  acknowledged_at?: string | null;
  close_reason?: string | null;
  component?: string | null;
  first_seen_at?: string | null;
  id: string;
  last_seen_at?: string | null;
  message?: string | null;
  owner?: string | null;
  postmortem?: string | null;
  severity: string;
  source?: string;
  status: string;
  status_history?: Array<{
    actor_id?: string | null;
    at?: string | null;
    changed_fields?: string[];
    close_reason?: string | null;
    from_status?: string | null;
    owner?: string | null;
    postmortem_configured?: boolean;
    to_status?: string | null;
  }>;
  title: string;
};

export type SystemAlertRuleRecord = {
  component?: string | null;
  condition_json?: Record<string, unknown>;
  created_at?: string | null;
  enabled?: boolean;
  id: string;
  name: string;
  notification_scope?: string | null;
  owner?: string | null;
  severity_min: string;
  source: string;
  updated_at?: string | null;
};

export type SystemAlertIncidentUpdatePayload = {
  close_reason?: string | null;
  owner?: string | null;
  postmortem?: string | null;
  status?: string | null;
};

export type SystemAlertSubscriptionPayload = {
  channel: string;
  enabled?: boolean;
  scope?: string | null;
  severity_min?: string;
  target: string;
};

export type SystemAlertSubscriptionMutationPayload = {
  channel?: string | null;
  enabled?: boolean | null;
  scope?: string | null;
  severity_min?: string | null;
  target?: string | null;
};

export type SystemAlertSubscriptionRecord = SystemAlertSubscriptionPayload & {
  created_at?: string | null;
  created_by?: string | null;
  id: string;
  updated_at?: string | null;
};

export type SystemAlertNotificationRecord = {
  alert_id: string;
  attempts?: number;
  channel: string;
  created_at?: string | null;
  id: string;
  last_error?: string | null;
  payload_json?: Record<string, unknown>;
  sent_at?: string | null;
  severity: string;
  status: string;
  subscription_id: string;
  target: string;
  updated_at?: string | null;
};

export type SystemAlertNotificationDispatchResult = {
  notifications: SystemAlertNotificationRecord[];
  remaining_pending_count: number;
  summary: {
    channel_counts?: Record<string, number>;
    failed_count?: number;
    include_failed?: boolean;
    processed_count?: number;
    sent_count?: number;
    skipped_count?: number;
  };
};

export type SystemAlertRuleMutationPayload = {
  component?: string | null;
  condition_json?: Record<string, unknown>;
  enabled?: boolean;
  name?: string | null;
  notification_scope?: string | null;
  owner?: string | null;
  severity_min?: string;
  source?: string | null;
};

export type SystemObjectStorageCleanupResult = {
  blocked_asset_count: number;
  cleaned_asset_ids: string[];
  confirmed: boolean;
  deleted_objects: Array<Record<string, unknown>>;
  dry_run: boolean;
  errors: Array<Record<string, unknown>>;
  metadata_only_cleanup_count: number;
  object_delete_count: number;
  planned_asset_cleanup_count: number;
  planned_object_delete_count: number;
  reason_configured: boolean;
  sample_blocked_assets: Array<Record<string, unknown>>;
  status: string;
};

export type SystemAdminWeeklyReport = {
  generated_at: string;
  markdown: string;
  sections?: Record<string, unknown>;
  summary: Record<string, unknown>;
  trace_id?: string;
};

export type SystemHealthKnowledgeGovernanceCandidate = {
  age_days?: number | null;
  document_id?: string | null;
  index_status?: string | null;
  knowledge_space_id?: string | null;
  knowledge_space_name?: string | null;
  product_id?: string | null;
  reason?: string | null;
  reasons?: string[];
  severity?: string | null;
  suggested_action?: string | null;
  title?: string | null;
  updated_at?: string | null;
};

export type SystemHealthOperations = {
  ai_executor_ops?: {
    controls?: Array<{ description: string; label: string; target: string }>;
    failure_reason_distribution?: Array<{ count?: number; reason?: string }>;
    latest_active_tasks?: Array<{
      ai_task_id?: string | null;
      created_at?: string | null;
      error_code?: string | null;
      error_message?: string | null;
      executor_type?: string | null;
      id?: string;
      runner_id?: string | null;
      scheduled_job_run_id?: string | null;
      status?: string;
      updated_at?: string | null;
    }>;
    latest_failures?: Array<{
      ai_task_id?: string | null;
      created_at?: string | null;
      error_code?: string | null;
      error_message?: string | null;
      executor_type?: string | null;
      id?: string;
      runner_id?: string | null;
      scheduled_job_run_id?: string | null;
      status?: string;
      updated_at?: string | null;
    }>;
    operation_targets?: {
      cancellable_count?: number;
      retryable_count?: number;
      timeout_scan_count?: number;
    };
    runner_health?: Record<string, unknown>;
    policies?: Record<string, unknown>;
    strategy_config?: {
      configuration_issues?: Array<Record<string, unknown>>;
      recommendation?: string;
      status?: string;
      strategy_matrix?: Array<Record<string, unknown>>;
      task_timeout_seconds?: Record<string, unknown>;
    };
    summary?: Record<string, unknown>;
    task_status_counts?: Record<string, number>;
  };
  alert_center?: {
    alerts: SystemHealthAlertRecord[];
    notifications?: SystemAlertNotificationRecord[];
    rules?: SystemAlertRuleRecord[];
    summary: {
      enabled_subscription_count?: number;
      failed_notification_count?: number;
      enabled_rule_count?: number;
      high_count: number;
      low_count: number;
      medium_count: number;
      open_count: number;
      pending_notification_count?: number;
      resolving_count?: number;
      rule_count?: number;
      sent_notification_count?: number;
      skipped_notification_count?: number;
      total_notification_count?: number;
    };
    subscriptions?: SystemAlertSubscriptionRecord[];
    trend?: Array<Record<string, unknown>>;
  };
  dingtalk_lifecycle?: {
    authorization_boundaries?: Array<Record<string, unknown>>;
    authorization_subject_summary?: Record<string, number>;
    authorization_subjects?: Array<Record<string, unknown>>;
    login?: Record<string, unknown>;
    mcp?: {
      connection_count?: number;
      failed_connection_count?: number;
      key_expiry_alerts?: Array<Record<string, unknown>>;
      soon_expiring_count?: number;
    };
    user_bindings?: Record<string, unknown>;
  };
  execution_governance?: {
    agent_loops?: { status_counts?: Record<string, number>; total?: number };
    execution_resources?: { active?: number; status_counts?: Record<string, number>; total?: number };
    external_event_inbox?: {
      dead_letter_count?: number;
      recent_dead_letters?: Array<Record<string, unknown>>;
      status_counts?: Record<string, number>;
      total?: number;
    };
    outbox?: { pending_count?: number; status_counts?: Record<string, number>; total?: number };
    quality_gates?: { status_counts?: Record<string, number>; total?: number };
  };
  help_and_retention?: {
    cleanup_status?: {
      cleanup_mode?: string;
      expired_records?: Array<Record<string, unknown>>;
      policies?: Array<Record<string, unknown>>;
      recommendation?: string;
      status?: string;
      total_expired_count?: number;
    };
    object_storage_cleanup?: {
      blocked_asset_count?: number;
      cleanup_failed_count?: number;
      cleanup_ready_count?: number;
      incomplete_asset_count?: number;
      metadata_only_cleanup_count?: number;
      orphan_asset_count?: number;
      recommendation?: string;
      sample_assets?: Array<Record<string, unknown>>;
      status?: string;
      tracked_asset_count?: number;
    };
    retention_policies?: Array<{
      configured: boolean;
      days: number;
      env: string;
      key: string;
      note: string;
      title: string;
    }>;
    screenshots?: {
      coverage?: Record<string, number>;
      screenshots?: Array<Record<string, unknown>>;
    };
  };
  knowledge_quality_loop?: {
    feedback_loop?: Record<string, unknown>;
    governance_candidates?: SystemHealthKnowledgeGovernanceCandidate[];
    governance_summary?: Record<string, unknown>;
    quality_gates?: Array<Record<string, unknown>>;
    summary?: Record<string, unknown>;
    watch_documents?: SystemHealthKnowledgeGovernanceCandidate[];
  };
  permission_diagnostics?: {
    auto_fix_suggestions?: Array<Record<string, unknown>>;
    diagnostics?: Array<Record<string, unknown>>;
    scope_comparison?: Record<string, Record<string, number>>;
    summary?: Record<string, unknown>;
  };
  product_onboarding_scores?: {
    products?: Array<{
      git_repository_count?: number;
      knowledge_document_count?: number;
      missing_items?: string[];
      module_count?: number;
      name: string;
      permission_scope_count?: number;
      permission_scope_status?: string;
      plugin_connection_count?: number;
      plugin_failed_connection_count?: number;
      plugin_total_connection_count?: number;
      product_id: string;
      recent_health_check?: {
        checked_at?: string | null;
        failed_knowledge_document_count?: number;
        failed_plugin_connection_count?: number;
        issues?: string[];
        status?: string;
        summary?: string;
      };
      recent_health_status?: string;
      related_system_count?: number;
      score: number;
      score_breakdown?: Array<{
        evidence?: string;
        key: string;
        label: string;
        max_score: number;
        score: number;
        status: string;
        suggestion?: string;
      }>;
      searchable_knowledge_document_count?: number;
      status: string;
      version_count?: number;
    }>;
    summary?: Record<string, unknown>;
  };
  security_audit_governance?: {
    admin_weekly_report?: Record<string, unknown>;
    audit_export?: Record<string, unknown>;
    governance_actions?: Array<Record<string, unknown>>;
    high_risk_confirmation?: Record<string, unknown>;
    secret_ref_validation?: {
      direct_secret_count?: number;
      invalid_ref_count?: number;
      issues?: Array<Record<string, unknown>>;
      ref_count?: number;
      status?: string;
      supported_formats?: string[];
    };
    sensitive_config_approval?: Record<string, unknown>;
  };
};

export type SystemHealthReport = {
  checked_at: string;
  checks: SystemHealthCheckRecord[];
  operations?: SystemHealthOperations;
  overall_status: string;
  platform?: Record<string, string>;
  recommendations: SystemHealthRecommendationRecord[];
  summary: {
    category_counts: Record<string, Record<string, number>>;
    critical_count: number;
    needs_attention_count: number;
    ok_count: number;
    status_counts: Record<string, number>;
    total: number;
  };
  trace_id: string;
};

export type RoleAccessPreview = {
  diagnostics: Array<{
    code: string;
    level: string;
    message: string;
    permission_codes?: string[];
  }>;
  granted_menu_codes: string[];
  granted_permission_codes: string[];
  high_risk_permission_codes: string[];
  high_risk_permission_count: number;
  menu_count: number;
  missing_menu_permission_codes: string[];
  operation_permissions: PermissionRecord[];
  permission_count: number;
  required_permission_codes: string[];
  role_code: string;
  role_id: string;
  role_name: string;
  scope_count: number;
  scope_groups: Array<{
    count: number;
    scope_type: string;
    scope_type_label: string;
    scopes: ScopeGrant[];
  }>;
  scope_summary: string;
  scopes: ScopeGrant[];
  visible_menus: MenuResourceRecord[];
};

export type SystemRoleRecord = UserRoleDefinition & {
  access_preview?: RoleAccessPreview;
  id: string;
  is_system: boolean;
  menu_codes: string[];
  permission_codes: string[];
  scopes: ScopeGrant[];
};

export type RbacPolicyMatrixRow = {
  category: string;
  diagnostics: Array<{
    code: string;
    level: string;
    message: string;
    permission_codes?: string[];
  }>;
  granted_menu_codes: string[];
  granted_permission_codes: string[];
  high_risk_permission_codes: string[];
  high_risk_permission_count: number;
  is_system: boolean;
  menu_count: number;
  missing_menu_permission_codes: string[];
  permission_count: number;
  required_permission_codes: string[];
  role_code: string;
  role_id: string;
  role_name: string;
  scope_count: number;
  scope_summary: string;
  scopes: ScopeGrant[];
  standalone_permission_codes: string[];
  status: string;
};

export type RbacPolicyMatrix = {
  menus: MenuResourceRecord[];
  permissions: PermissionRecord[];
  roles: SystemRoleRecord[];
  rows: RbacPolicyMatrixRow[];
  summary: {
    active_role_count: number;
    menu_count: number;
    permission_count: number;
    role_count: number;
    roles_with_high_risk_permissions: number;
    roles_with_menu_permission_gaps: number;
    scope_grant_count: number;
  };
};

export type UserPermissionDiagnosticCheck = {
  code: string;
  granted_by_roles?: Array<{
    role_code: string;
    role_name: string;
  }>;
  granted_menu_code?: string | null;
  known?: boolean;
  matched_menu?: {
    code: string;
    name?: string;
    path?: string;
  };
  matched_scopes?: ScopeGrant[];
  message: string;
  missing_permission_codes?: string[];
  permission?: {
    code: string;
    name?: string;
    risk_level?: string | null;
  };
  required_permission_codes?: string[];
  role_codes?: string[];
  status: 'allowed' | 'blocked' | string;
  target?: string;
};

export type UserPermissionDiagnostic = {
  checks: UserPermissionDiagnosticCheck[];
  decision: {
    allowed: boolean;
    blocked_reasons: string[];
    granted_reasons: string[];
  };
  effective: {
    menu_codes: string[];
    permission_codes: string[];
    role_codes: string[];
    scopes: ScopeGrant[];
  };
  user: {
    display_name?: string;
    id: string;
    roles: string[];
    status: string;
    username?: string;
  };
};

export type UserMenuPreview = {
  blocked_menus: Array<{
    code: string;
    message: string;
    missing_permission_codes?: string[];
    name?: string;
    path?: string | null;
    reason: string;
    required_permission_codes?: string[];
  }>;
  effective: {
    menu_codes: string[];
    permission_codes: string[];
    role_codes: string[];
    scopes: ScopeGrant[];
  };
  menu_tree: Array<{
    children?: UserMenuPreview['menu_tree'];
    code: string;
    name: string;
    path?: string | null;
  }>;
  scope_summary?: string;
  summary: {
    blocked_menu_count: number;
    granted_menu_count: number;
    visible_menu_count: number;
  };
  user: {
    display_name?: string;
    id: string;
    roles: string[];
    status: string;
    username?: string;
  };
  visible_menu_codes: string[];
  visible_menus: Array<{ code: string; name?: string; path?: string | null }>;
};

export type RoleRiskPrecheck = {
  auto_fix_suggestions: Array<{
    action: string;
    description: string;
    permission_codes?: string[];
    scope_examples?: ScopeGrant[];
  }>;
  candidate: RoleAccessPreview;
  current: RoleAccessPreview;
  decision: {
    can_save: boolean;
    risk_count: number;
    status: 'pass' | 'warning' | 'blocked' | string;
  };
  risks: Array<{
    code: string;
    level?: string;
    message: string;
    permission_codes?: string[];
    severity: string;
  }>;
  scope_comparison: {
    candidate: Record<string, Record<string, number>>;
    current: Record<string, Record<string, number>>;
  };
};

export type UserMutationPayload = {
  display_name?: string;
  mobile?: string;
  password?: string;
  roles?: string[];
  status?: string;
  username?: string;
};

type UserListItem = {
  dingtalk_binding?: {
    bound: boolean;
    corp_id?: string | null;
    corp_name?: string | null;
    display_name?: string | null;
    email?: string | null;
    identity_id?: string | null;
    provider?: string;
  };
  display_name: string;
  id: string;
  local_password_configured?: boolean;
  login_methods?: string[];
  mobile?: string;
  roles?: string[];
  status?: string;
  username: string;
};

type RoleDefinitionListItem = {
  business_roles?: string[];
  category?: string;
  code: string;
  data_scope?: string;
  decision_scope?: string;
  description?: string;
  is_assignable?: boolean;
  is_system?: boolean;
  limitations?: string[];
  menu_codes?: string[];
  menu_scope?: string[];
  name: string;
  permission_codes?: string[];
  permissions?: string[];
  responsibilities?: string[];
  scopes?: ScopeGrant[];
  access_preview?: RoleAccessPreview;
  id?: string;
  sort_order?: number;
  status?: string;
};

function mapRoleDefinition(role: RoleDefinitionListItem): UserRoleDefinition {
  return {
    business_roles: role.business_roles ?? [],
    category: role.category ?? 'workspace',
    code: role.code,
    data_scope: role.data_scope ?? '',
    decision_scope: role.decision_scope ?? '',
    description: role.description ?? '',
    is_assignable: role.is_assignable ?? true,
    limitations: role.limitations ?? [],
    menu_scope: role.menu_scope ?? role.menu_codes ?? [],
    name: role.name,
    permissions: role.permissions ?? role.permission_codes ?? [],
    responsibilities: role.responsibilities ?? [],
    sort_order: role.sort_order ?? 0,
    status: role.status ?? 'active',
  };
}

function mapSystemRole(role: RoleDefinitionListItem): SystemRoleRecord {
  const roleDefinition = mapRoleDefinition(role);
  return {
    ...roleDefinition,
    id: role.id ?? role.code,
    access_preview: role.access_preview,
    is_system: role.is_system ?? false,
    menu_codes: role.menu_codes ?? role.menu_scope ?? [],
    permission_codes: role.permission_codes ?? role.permissions ?? [],
    scopes: role.scopes ?? [],
  };
}

export async function fetchRoleDefinitions(): Promise<UserRoleDefinition[]> {
  const token = requireAccessToken();
  const roles = await apiRequest<ListResponse<RoleDefinitionListItem>>('/api/auth/roles', { token });
  return roles.items.map(mapRoleDefinition);
}

export async function fetchRoleDefinitionList(
  query: RoleListQuery = {},
): Promise<RemoteListResult<UserRoleDefinition>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'business_role', query.businessRole);
  appendQueryParam(params, 'category', query.category);
  appendQueryParam(params, 'menu_scope', query.menuScope);
  appendQueryParam(params, 'permission', query.permission);
  appendQueryParam(params, 'role', query.role);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const roles = await apiRequest<ListResponse<RoleDefinitionListItem>>(
    queryString ? `/api/auth/roles?${queryString}` : '/api/auth/roles',
    { token },
  );
  return {
    page: roles.page ?? query.page ?? 1,
    pageSize: roles.page_size ?? query.pageSize ?? 10,
    rows: roles.items.map(mapRoleDefinition),
    total: roles.total,
  };
}

export async function fetchSystemPermissions(): Promise<PermissionRecord[]> {
  const token = requireAccessToken();
  const permissions = await apiRequest<{ items: PermissionRecord[] }>('/api/system/permissions', {
    token,
  });
  return permissions.items;
}

export async function fetchSystemMenus(): Promise<MenuResourceRecord[]> {
  const token = requireAccessToken();
  const menus = await apiRequest<{ items: MenuResourceRecord[] }>('/api/system/menus', { token });
  return menus.items;
}

export async function fetchSystemSettings(): Promise<SystemSettingsRecord> {
  const token = requireAccessToken();
  return apiRequest<SystemSettingsRecord>('/api/system/settings', { token });
}

export async function updateSystemSettings(
  payload: SystemSettingsMutationPayload,
): Promise<SystemSettingsRecord> {
  const token = requireAccessToken();
  return apiRequest<SystemSettingsRecord>('/api/system/settings', {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function testSystemEmailDelivery(
  payload: SystemEmailDeliveryTestPayload,
): Promise<SystemEmailDeliveryTestResult> {
  const token = requireAccessToken();
  return apiRequest<SystemEmailDeliveryTestResult>('/api/system/settings/email/test', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function fetchSystemHealth(): Promise<SystemHealthReport> {
  const token = requireAccessToken();
  return apiRequest<SystemHealthReport>('/api/system/health', { token });
}

export async function fetchSystemAdminWeeklyReport(
  days = 7,
): Promise<SystemAdminWeeklyReport> {
  const token = requireAccessToken();
  return apiRequest<SystemAdminWeeklyReport>(`/api/system/admin-weekly-report?days=${days}`, {
    token,
  });
}

export async function updateSystemAlertIncident(
  alertId: string,
  payload: SystemAlertIncidentUpdatePayload,
): Promise<SystemHealthAlertRecord> {
  const token = requireAccessToken();
  return apiRequest<SystemHealthAlertRecord>(
    `/api/system/alerts/${encodeURIComponent(alertId)}`,
    {
      body: payload,
      method: 'PATCH',
      token,
    },
  );
}

export async function createSystemAlertSubscription(
  payload: SystemAlertSubscriptionPayload,
): Promise<SystemAlertSubscriptionRecord> {
  const token = requireAccessToken();
  return apiRequest<SystemAlertSubscriptionRecord>('/api/system/alerts/subscriptions', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateSystemAlertSubscription(
  subscriptionId: string,
  payload: SystemAlertSubscriptionMutationPayload,
): Promise<SystemAlertSubscriptionRecord> {
  const token = requireAccessToken();
  return apiRequest<SystemAlertSubscriptionRecord>(
    `/api/system/alerts/subscriptions/${encodeURIComponent(subscriptionId)}`,
    {
      body: payload,
      method: 'PATCH',
      token,
    },
  );
}

export async function dispatchSystemAlertNotifications(payload: {
  include_failed?: boolean;
  limit?: number;
} = {}): Promise<SystemAlertNotificationDispatchResult> {
  const token = requireAccessToken();
  return apiRequest<SystemAlertNotificationDispatchResult>(
    '/api/system/alerts/notifications/dispatch',
    {
      body: payload,
      method: 'POST',
      token,
    },
  );
}

export async function createSystemAlertRule(
  payload: SystemAlertRuleMutationPayload,
): Promise<SystemAlertRuleRecord> {
  const token = requireAccessToken();
  return apiRequest<SystemAlertRuleRecord>('/api/system/alerts/rules', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateSystemAlertRule(
  ruleId: string,
  payload: SystemAlertRuleMutationPayload,
): Promise<SystemAlertRuleRecord> {
  const token = requireAccessToken();
  return apiRequest<SystemAlertRuleRecord>(
    `/api/system/alerts/rules/${encodeURIComponent(ruleId)}`,
    {
      body: payload,
      method: 'PATCH',
      token,
    },
  );
}

export async function cleanupSystemObjectStorage(payload: {
  confirmed?: boolean;
  reason?: string | null;
}): Promise<SystemObjectStorageCleanupResult> {
  const token = requireAccessToken();
  return apiRequest<SystemObjectStorageCleanupResult>('/api/system/object-storage/cleanup', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function fetchSystemMenuList(
  query: MenuListQuery = {},
): Promise<RemoteListResult<MenuResourceRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'menu', query.menu);
  appendQueryParam(params, 'menu_type', query.menuType);
  appendQueryParam(params, 'parent', query.parent);
  appendQueryParam(params, 'path', query.path);
  appendQueryParam(params, 'permission', query.permission);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const menus = await apiRequest<ListResponse<MenuResourceRecord>>(
    queryString ? `/api/system/menus?${queryString}` : '/api/system/menus',
    { token },
  );
  return {
    page: menus.page ?? query.page ?? 1,
    pageSize: menus.page_size ?? query.pageSize ?? 10,
    performance: menus.performance,
    rows: menus.items,
    total: menus.total,
  };
}

export async function fetchSystemPermissionMatrix(): Promise<RbacPolicyMatrix> {
  const token = requireAccessToken();
  const matrix = await apiRequest<RbacPolicyMatrix>('/api/system/permissions/matrix', { token });
  return {
    ...matrix,
    roles: matrix.roles.map(mapSystemRole),
  };
}

export async function fetchSystemPermissionDiagnostics(query: {
  path?: string;
  permissionCode?: string;
  scopeId?: string;
  scopeType?: string;
  userId: string;
}): Promise<UserPermissionDiagnostic> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'user_id', query.userId);
  appendQueryParam(params, 'path', query.path);
  appendQueryParam(params, 'permission_code', query.permissionCode);
  appendQueryParam(params, 'scope_type', query.scopeType);
  appendQueryParam(params, 'scope_id', query.scopeId);
  return apiRequest<UserPermissionDiagnostic>(`/api/system/permissions/diagnostics?${params.toString()}`, {
    token,
  });
}

export async function fetchSystemUserMenuPreview(userId: string): Promise<UserMenuPreview> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'user_id', userId);
  return apiRequest<UserMenuPreview>(`/api/system/permissions/menu-preview?${params.toString()}`, {
    token,
  });
}

export async function fetchSystemRoleRiskPrecheck(
  roleId: string,
  payload: {
    menu_codes?: string[];
    permission_codes?: string[];
    scopes?: ScopeGrant[];
    status?: string;
  },
): Promise<RoleRiskPrecheck> {
  const token = requireAccessToken();
  return apiRequest<RoleRiskPrecheck>(`/api/system/roles/${roleId}/risk-precheck`, {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function createSystemMenu(
  payload: MenuResourceMutationPayload & { code: string; name: string },
): Promise<MenuResourceRecord> {
  const token = requireAccessToken();
  return apiRequest<MenuResourceRecord>('/api/system/menus', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateSystemMenu(
  menuCode: string,
  payload: MenuResourceMutationPayload,
): Promise<MenuResourceRecord> {
  const token = requireAccessToken();
  return apiRequest<MenuResourceRecord>(`/api/system/menus/${menuCode}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function setSystemMenuStatus(
  menuCode: string,
  status: 'active' | 'inactive',
): Promise<MenuResourceRecord> {
  const token = requireAccessToken();
  const action = status === 'active' ? 'enable' : 'disable';
  return apiRequest<MenuResourceRecord>(`/api/system/menus/${menuCode}/${action}`, {
    method: 'POST',
    token,
  });
}

export async function deleteSystemMenu(menuCode: string): Promise<{ code: string; deleted: boolean }> {
  const token = requireAccessToken();
  return apiRequest<{ code: string; deleted: boolean }>(`/api/system/menus/${menuCode}`, {
    method: 'DELETE',
    token,
  });
}

export async function reorderSystemMenus(
  items: Array<{ code: string; sort_order: number }>,
): Promise<MenuResourceRecord[]> {
  const token = requireAccessToken();
  const response = await apiRequest<{ items: MenuResourceRecord[] }>('/api/system/menus/reorder', {
    body: { items },
    method: 'PUT',
    token,
  });
  return response.items;
}

export async function fetchSystemRoleList(
  query: RoleListQuery = {},
): Promise<RemoteListResult<SystemRoleRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'business_role', query.businessRole);
  appendQueryParam(params, 'category', query.category);
  appendQueryParam(params, 'menu_scope', query.menuScope);
  appendQueryParam(params, 'permission', query.permission);
  appendQueryParam(params, 'role', query.role);
  appendQueryParam(params, 'status', query.status);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const roles = await apiRequest<ListResponse<RoleDefinitionListItem>>(
    queryString ? `/api/system/roles?${queryString}` : '/api/system/roles',
    { token },
  );
  return {
    page: roles.page ?? query.page ?? 1,
    pageSize: roles.page_size ?? query.pageSize ?? 10,
    performance: roles.performance,
    rows: roles.items.map(mapSystemRole),
    total: roles.total,
  };
}

export async function createSystemRole(payload: {
  category: string;
  code: string;
  description?: string;
  is_assignable?: boolean;
  name: string;
  sort_order?: number;
}): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>('/api/system/roles', {
    body: payload,
    method: 'POST',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRole(
  roleId: string,
  payload: {
    category?: string;
    description?: string;
    is_assignable?: boolean;
    name?: string;
    sort_order?: number;
  },
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
  return mapSystemRole(role);
}

export async function copySystemRole(
  roleId: string,
  payload: {
    code: string;
    description?: string;
    name?: string;
  },
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/copy`, {
    body: payload,
    method: 'POST',
    token,
  });
  return mapSystemRole(role);
}

export async function setSystemRoleStatus(
  roleId: string,
  status: 'active' | 'inactive',
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const action = status === 'active' ? 'enable' : 'disable';
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/${action}`, {
    method: 'POST',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRolePermissions(
  roleId: string,
  permissionCodes: string[],
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/permissions`, {
    body: { permission_codes: permissionCodes },
    method: 'PUT',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRoleMenus(
  roleId: string,
  menuCodes: string[],
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/menus`, {
    body: { menu_codes: menuCodes },
    method: 'PUT',
    token,
  });
  return mapSystemRole(role);
}

export async function updateSystemRoleScopes(
  roleId: string,
  scopes: ScopeGrant[],
): Promise<SystemRoleRecord> {
  const token = requireAccessToken();
  const role = await apiRequest<RoleDefinitionListItem>(`/api/system/roles/${roleId}/scopes`, {
    body: { scopes },
    method: 'PUT',
    token,
  });
  return mapSystemRole(role);
}

export async function fetchManagementUsers(
  roleDefinitions: UserRoleDefinition[] = [],
): Promise<UserRecord[]> {
  const token = requireAccessToken();
  const users = await apiRequest<ListResponse<UserListItem>>('/api/users', { token });

  return users.items.map((user) => {
    const roles = user.roles ?? [];
    return {
      displayName: user.display_name,
      dingtalkBinding: user.dingtalk_binding,
      id: user.id,
      localPasswordConfigured: user.local_password_configured ?? true,
      loginMethods: user.login_methods ?? [],
      mobile: user.mobile ?? '',
      roles,
      rolesText: formatUserRoles(roles, roleDefinitions),
      status: user.status === 'inactive' ? 'inactive' : 'active',
      username: user.username,
    };
  });
}

export async function fetchManagementUserList(
  roleDefinitions: UserRoleDefinition[] = [],
  query: UserListQuery = {},
): Promise<RemoteListResult<UserRecord>> {
  const token = requireAccessToken();
  const params = new URLSearchParams();
  appendQueryParam(params, 'display_name', query.displayName);
  appendQueryParam(params, 'role', query.role);
  appendQueryParam(params, 'status', query.status);
  appendQueryParam(params, 'username', query.username);
  appendRemoteListParams(params, query);
  const queryString = params.toString();
  const users = await apiRequest<ListResponse<UserListItem>>(
    queryString ? `/api/users?${queryString}` : '/api/users',
    { token },
  );

  return {
    page: users.page ?? query.page ?? 1,
    pageSize: users.page_size ?? query.pageSize ?? 10,
    performance: users.performance,
    rows: users.items.map((user) => {
      const roles = user.roles ?? [];
      return {
        displayName: user.display_name,
        dingtalkBinding: user.dingtalk_binding,
        id: user.id,
        localPasswordConfigured: user.local_password_configured ?? true,
        loginMethods: user.login_methods ?? [],
        mobile: user.mobile ?? '',
        roles,
        rolesText: formatUserRoles(roles, roleDefinitions),
        status: user.status === 'inactive' ? 'inactive' : 'active',
        username: user.username,
      };
    }),
    total: users.total,
  };
}

export async function createManagementUser(payload: UserMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<UserListItem>('/api/users', {
    body: payload,
    method: 'POST',
    token,
  });
}

export async function updateManagementUser(userId: string, payload: UserMutationPayload) {
  const token = requireAccessToken();
  return apiRequest<UserListItem>(`/api/users/${userId}`, {
    body: payload,
    method: 'PATCH',
    token,
  });
}

export async function deleteManagementUser(userId: string) {
  const token = requireAccessToken();
  return apiRequest<{ deleted: boolean; id: string }>(`/api/users/${userId}`, {
    method: 'DELETE',
    token,
  });
}

export async function unbindSystemExternalIdentity(identityId: string, force = false) {
  const token = requireAccessToken();
  const query = force ? '?force=true' : '';
  return apiRequest<{ deleted: boolean; id: string }>(
    `/api/system/external-identities/${identityId}${query}`,
    {
      method: 'DELETE',
      token,
    },
  );
}
