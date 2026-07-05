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
