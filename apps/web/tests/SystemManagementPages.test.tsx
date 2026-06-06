import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import RolesPage from '../src/pages/Roles';
import UsersPage from '../src/pages/Users';

const roleCatalogEnvelope = {
  data: {
    items: [
      {
        business_roles: ['平台管理员'],
        code: 'admin',
        data_scope: '全平台。',
        decision_scope: '系统治理。',
        description: '负责用户、角色、模型网关、审计与系统级配置管理。',
        is_assignable: true,
        limitations: ['不能代替业务负责人做最终产品决策。'],
        menu_scope: ['系统管理', '审计与运行'],
        name: '系统管理员',
        permissions: ['system.users.manage'],
        responsibilities: ['维护用户和角色。'],
        sort_order: 10,
        status: 'active',
      },
      {
        business_roles: ['只读参与者'],
        code: 'viewer',
        data_scope: '授权范围内的数据。',
        decision_scope: '无写入或审批决策权限。',
        description: '只能查看有权限访问的工作台数据、任务结果、知识和看板摘要。',
        is_assignable: true,
        limitations: ['不能执行写操作、审批或配置变更。'],
        menu_scope: ['首页 IT 团队看板', '授权业务列表'],
        name: '查看者',
        permissions: ['workspace.read'],
        responsibilities: ['查看授权范围内的业务数据。'],
        sort_order: 60,
        status: 'active',
      },
    ],
    total: 2,
  },
};

describe('system management pages', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('uses explicitly defined role options in the user management modal', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (String(input) === '/api/auth/roles') {
        expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
        return new Response(JSON.stringify(roleCatalogEnvelope), {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        });
      }
      expect(String(input)).toMatch(/^\/api\/users\?/);
      expect(String(input)).toContain('page=1');
      expect(String(input)).toContain('page_size=10');
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      return new Response(
        JSON.stringify({
          data: {
            items: [],
            page: 1,
            page_size: 10,
            total: 0,
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      );
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<UsersPage />);

    fireEvent.click(screen.getByRole('button', { name: /新增用户/ }));

    expect((await screen.findAllByText(/查看者/)).length).toBeGreaterThan(0);
    expect(screen.queryByPlaceholderText('admin, product_owner, rd_owner')).not.toBeInTheDocument();
  });

  it('renders system role management from the backend role catalog', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(String(input)).toMatch(/^\/api\/auth\/roles\?/);
      expect(String(input)).toContain('page=1');
      expect(String(input)).toContain('page_size=10');
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      return new Response(
        JSON.stringify({
          data: {
            ...roleCatalogEnvelope.data,
            page: 1,
            page_size: 10,
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      );
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<RolesPage />);

    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('系统管理');
    expect(await screen.findByText('角色定义')).toBeInTheDocument();
    expect(screen.getByText('系统管理员')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
    expect(screen.getByText('查看者')).toBeInTheDocument();
    expect(screen.getByText('viewer')).toBeInTheDocument();
    expect(screen.getByText('平台管理员')).toBeInTheDocument();
    expect(screen.getByText('只读参与者')).toBeInTheDocument();
    expect(screen.getAllByText('系统管理').length).toBeGreaterThan(0);
    expect(screen.getAllByText('2 个入口').length).toBeGreaterThan(0);
    expect(screen.getAllByText('1 个权限点')).toHaveLength(2);
    expect(screen.getByText('职责与范围')).toBeInTheDocument();
    expect(screen.queryByText('负责用户、角色、模型网关、审计与系统级配置管理。')).not.toBeInTheDocument();
    expect(screen.queryByText('全平台。')).not.toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: '详情' })[0]);

    expect(await screen.findByRole('dialog', { name: '角色详情 · 系统管理员' })).toBeInTheDocument();
    expect(screen.getByText('负责用户、角色、模型网关、审计与系统级配置管理。')).toBeInTheDocument();
    expect(screen.getByText('全平台。')).toBeInTheDocument();
    expect(screen.getByText('系统治理。')).toBeInTheDocument();
    expect(screen.getByText('维护用户和角色。')).toBeInTheDocument();
    expect(screen.getByText('不能代替业务负责人做最终产品决策。')).toBeInTheDocument();
    expect(screen.getByText('system.users.manage')).toBeInTheDocument();
    expect(screen.getByText('审计与运行')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /新增角色|删除/ })).not.toBeInTheDocument();
  });
});
