export type UserRoleCode =
  | 'admin'
  | 'product_owner'
  | 'rd_owner'
  | 'reviewer'
  | 'knowledge_owner'
  | 'viewer';

export type UserRoleDefinition = {
  category: string;
  code: UserRoleCode | string;
  data_scope: string;
  decision_scope: string;
  description: string;
  is_assignable: boolean;
  name: string;
  permissions: string[];
  responsibilities: string[];
  sort_order: number;
  status: string;
};

export type UserRoleOption = {
  description: string;
  label: string;
  permissions: string[];
  value: string;
};

export function toUserRoleOptions(roleDefinitions: UserRoleDefinition[]): UserRoleOption[] {
  return roleDefinitions
    .filter((role) => role.is_assignable && role.status === 'active')
    .sort((left, right) => left.sort_order - right.sort_order)
    .map((role) => ({
      description: role.description,
      label: `${role.name} (${role.code})`,
      permissions: role.permissions,
      value: role.code,
    }));
}

export function formatUserRoles(
  roles: string[] | undefined,
  roleDefinitions: UserRoleDefinition[] = [],
): string {
  if (!roles?.length) {
    return '-';
  }

  const roleLabelByCode = Object.fromEntries(
    roleDefinitions.map((role) => [role.code, role.name]),
  ) as Record<string, string>;

  return roles.map((role) => roleLabelByCode[role] ?? role).join(', ');
}
