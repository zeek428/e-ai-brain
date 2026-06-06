import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import './proComponentsMock';

import { ManagementListPage } from '../src/components/ManagementListPage';

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
});
