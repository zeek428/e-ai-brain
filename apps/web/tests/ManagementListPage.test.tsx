import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import './proComponentsMock';

import { ManagementListPage } from '../src/components/ManagementListPage';

afterEach(() => {
  cleanup();
});

describe('ManagementListPage', () => {
  it('applies stable defaults to management list tables', () => {
    render(
      <ManagementListPage
        breadcrumbGroup="系统管理"
        columns={[
          { dataIndex: 'name', title: '名称' },
          {
            dataIndex: 'summary',
            render: (value) => <span>{String(value)}</span>,
            title: '摘要',
          },
          {
            key: 'actions',
            render: () => <button type="button">详情</button>,
            title: '操作',
            valueType: 'option',
          },
        ]}
        dataSource={[{ id: 'row_1', name: '长文本列', summary: '带自定义渲染的长文本列' }]}
        filters={[]}
        rowKey="id"
        tableTitle="测试列表"
        title="测试管理"
      />,
    );

    const table = screen.getByRole('table');
    expect(table).toHaveAttribute('data-table-layout', 'fixed');
    expect(table.closest('.management-list-table')).toBeInTheDocument();
    expect(Number(table.getAttribute('data-table-scroll-x'))).toBeGreaterThanOrEqual(960);
    expect(screen.getByRole('columnheader', { name: '名称' })).toHaveAttribute(
      'data-ellipsis',
      'true',
    );
    expect(screen.getByRole('columnheader', { name: '名称' })).toHaveAttribute(
      'data-width',
      '160',
    );
    expect(screen.getByRole('columnheader', { name: '摘要' })).toHaveAttribute(
      'data-width',
      '160',
    );
    expect(screen.getByRole('columnheader', { name: '操作' })).toHaveAttribute(
      'data-fixed',
      'right',
    );
    expect(screen.getByRole('columnheader', { name: '操作' })).toHaveAttribute(
      'data-width',
      '220',
    );
  });

  it('saves current filters as a reusable local filter view', async () => {
    window.localStorage.clear();

    render(
      <ManagementListPage
        breadcrumbGroup="系统管理"
        columns={[
          { dataIndex: 'name', title: '名称' },
          { dataIndex: 'status', title: '状态' },
        ]}
        dataSource={[{ id: 'row_1', name: '研发任务', status: 'active' }]}
        filters={[
          { label: '名称', name: 'name', type: 'text' },
          {
            label: '状态',
            name: 'status',
            options: [{ label: '启用', value: 'active' }],
            type: 'select',
          },
        ]}
        rowKey="id"
        tableTitle="测试列表"
        title="测试管理"
        viewStorageKey="test-management-list"
      />,
    );

    fireEvent.change(screen.getByLabelText('名称'), { target: { value: '研发' } });
    fireEvent.change(screen.getByLabelText('状态'), { target: { value: 'active' } });
    fireEvent.click(screen.getByRole('button', { name: '查询' }));
    fireEvent.click(screen.getByRole('button', { name: '保存视图' }));
    fireEvent.change(screen.getByLabelText('筛选视图名称'), { target: { value: '启用任务' } });
    fireEvent.click(screen.getByRole('button', { name: '保存筛选视图' }));

    await waitFor(() => {
      const storedViews = JSON.parse(
        window.localStorage.getItem(
          'ai-brain:management-list-filter-views:test-management-list',
        ) ?? '[]',
      );
      expect(storedViews).toMatchObject([
        {
          name: '启用任务',
          query: {
            filters: {
              name: '研发',
              status: 'active',
            },
          },
        },
      ]);
    });
  });
});
