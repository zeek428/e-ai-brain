import { describe, expect, it } from 'vitest';

import { formatUserRoles, toUserRoleOptions, type UserRoleDefinition } from '../src/data/roles';

const roleDefinitions: UserRoleDefinition[] = [
  {
    category: 'readonly',
    code: 'viewer',
    data_scope: '授权范围内的数据。',
    decision_scope: '无写权限。',
    description: '只能查看。',
    is_assignable: true,
    name: '查看者',
    permissions: ['workspace.read'],
    responsibilities: ['查看任务结果。'],
    sort_order: 60,
    status: 'active',
  },
  {
    category: 'system',
    code: 'admin',
    data_scope: '全平台。',
    decision_scope: '系统治理。',
    description: '管理系统。',
    is_assignable: true,
    name: '系统管理员',
    permissions: ['system.users.manage'],
    responsibilities: ['维护用户和角色。'],
    sort_order: 10,
    status: 'active',
  },
  {
    category: 'legacy',
    code: 'retired',
    data_scope: '不可分配。',
    decision_scope: '不可分配。',
    description: '停用角色。',
    is_assignable: false,
    name: '停用角色',
    permissions: [],
    responsibilities: ['不可分配。'],
    sort_order: 99,
    status: 'inactive',
  },
];

describe('role catalog helpers', () => {
  it('builds assignable options from backend role definitions', () => {
    expect(toUserRoleOptions(roleDefinitions)).toEqual([
      {
        description: '管理系统。',
        label: '系统管理员 (admin)',
        permissions: ['system.users.manage'],
        value: 'admin',
      },
      {
        description: '只能查看。',
        label: '查看者 (viewer)',
        permissions: ['workspace.read'],
        value: 'viewer',
      },
    ]);
  });

  it('formats user roles using the loaded catalog and keeps unknown codes visible', () => {
    expect(formatUserRoles(['admin', 'unknown'], roleDefinitions)).toBe('系统管理员, unknown');
  });
});
