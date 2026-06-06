import type React from 'react';
import { vi } from 'vitest';

vi.mock('@ant-design/pro-components', async () => {
  const React = await import('react');

  function PageContainer({
    breadcrumb,
    children,
    content,
    extra,
    title,
  }: {
    breadcrumb?: { items?: Array<{ title: React.ReactNode }> };
    children?: React.ReactNode;
    content?: React.ReactNode;
    extra?: React.ReactNode;
    title?: React.ReactNode;
  }) {
    return React.createElement(
      'main',
      null,
      breadcrumb?.items?.length
        ? React.createElement(
            'nav',
            { 'aria-label': '面包屑' },
            breadcrumb.items.map((item) =>
              React.createElement('span', { key: String(item.title) }, item.title),
            ),
          )
        : null,
      React.createElement('h1', null, title),
      content ? React.createElement('p', null, content) : null,
      extra,
      children,
    );
  }

  function ProCard({
    children,
    extra,
    title,
  }: {
    children?: React.ReactNode;
    extra?: React.ReactNode;
    title?: React.ReactNode;
  }) {
    return React.createElement(
      'section',
      null,
      title ? React.createElement('h2', null, title) : null,
      extra,
      children,
    );
  }

  ProCard.Group = ({ children }: { children?: React.ReactNode }) =>
    React.createElement('section', null, children);

  function ProTable<Row extends { [key: string]: unknown }>({
    className,
    columns,
    dataSource,
    headerTitle,
    onReset,
    onSubmit,
    rowKey,
    rowSelection,
    scroll,
    tableLayout,
    toolBarRender,
  }: {
    className?: string;
    columns: Array<{
      dataIndex?: keyof Row;
      ellipsis?: boolean;
      fixed?: string;
      hideInTable?: boolean;
      key?: string;
      render?: (value: unknown, row: Row) => React.ReactNode;
      search?: false;
      title: React.ReactNode;
      valueEnum?: Record<string, { text: React.ReactNode }>;
      valueType?: string;
      width?: number;
    }>;
    dataSource: Row[];
    headerTitle?: React.ReactNode;
    onReset?: () => void;
    onSubmit?: (values: Record<string, unknown>) => void;
    rowKey: keyof Row;
    rowSelection?: {
      getCheckboxProps?: (record: Row) => { disabled?: boolean };
      onChange?: (selectedRowKeys: React.Key[], selectedRows: Row[]) => void;
      selectedRowKeys?: React.Key[];
    };
    scroll?: { x?: number | string | true };
    tableLayout?: string;
    toolBarRender?: () => React.ReactNode[];
  }) {
    const searchColumns = columns.filter((column) => column.search !== false);
    const tableColumns = columns.filter((column) => !column.hideInTable);
    const selectedKeys = new Set((rowSelection?.selectedRowKeys ?? []).map(String));
    const toggleSelection = (row: Row, checked: boolean) => {
      const rowId = String(row[rowKey]);
      const nextKeys = checked
        ? [...selectedKeys, rowId]
        : [...selectedKeys].filter((selectedKey) => selectedKey !== rowId);
      rowSelection?.onChange?.(
        nextKeys,
        dataSource.filter((item) => nextKeys.includes(String(item[rowKey]))),
      );
    };

    return React.createElement(
      'section',
      { className },
      headerTitle ? React.createElement('h2', null, headerTitle) : null,
      React.createElement(
        'form',
        {
          'aria-label': '查询表格',
          onReset: () => onReset?.(),
          onSubmit: (event: React.FormEvent<HTMLFormElement>) => {
            event.preventDefault();
            const values: Record<string, unknown> = Object.fromEntries(
              new FormData(event.currentTarget),
            );
            Object.entries({ ...values }).forEach(([key, value]) => {
              if (key.endsWith('__start')) {
                const name = key.replace(/__start$/, '');
                values[name] = [value, values[`${name}__end`] ?? ''];
                delete values[key];
                delete values[`${name}__end`];
              }
            });
            onSubmit?.(values);
          },
        },
        searchColumns.map((column) =>
          React.createElement(
            'label',
            { key: String(column.dataIndex) },
            column.title,
            column.valueType === 'dateRange'
              ? React.createElement(
                  React.Fragment,
                  null,
                  React.createElement(
                    'label',
                    null,
                    `${column.title} 开始`,
                    React.createElement('input', {
                      name: `${String(column.dataIndex)}__start`,
                      type: 'date',
                    }),
                  ),
                  React.createElement(
                    'label',
                    null,
                    `${column.title} 结束`,
                    React.createElement('input', {
                      name: `${String(column.dataIndex)}__end`,
                      type: 'date',
                    }),
                  ),
                )
              : column.valueType === 'select'
                ? React.createElement(
                    'select',
                    { name: String(column.dataIndex) },
                    React.createElement('option', { value: '' }, '全部'),
                    Object.entries(column.valueEnum ?? {}).map(([value, option]) =>
                      React.createElement('option', { key: value, value }, option.text),
                    ),
                  )
                : React.createElement('input', { name: String(column.dataIndex), type: 'text' }),
          ),
        ),
        React.createElement('button', { type: 'submit' }, '查询'),
        React.createElement('button', { type: 'reset' }, '重置'),
      ),
      toolBarRender?.(),
      React.createElement(
        'table',
        {
          'data-table-layout': tableLayout,
          'data-table-scroll-x': scroll?.x === undefined ? undefined : String(scroll.x),
        },
        React.createElement(
          'thead',
          null,
          React.createElement(
            'tr',
            null,
            rowSelection ? React.createElement('th', { key: '__selection' }, '选择') : null,
            tableColumns.map((column) =>
              React.createElement(
                'th',
                {
                  'data-ellipsis': column.ellipsis ? 'true' : undefined,
                  'data-fixed': column.fixed,
                  'data-width': column.width === undefined ? undefined : String(column.width),
                  key: String(column.key ?? column.dataIndex),
                },
                column.title,
              ),
            ),
          ),
        ),
        React.createElement(
          'tbody',
          null,
          dataSource.map((row) =>
            React.createElement(
              'tr',
              { key: String(row[rowKey]) },
              rowSelection
                ? React.createElement(
                    'td',
                    { key: '__selection' },
                    React.createElement('input', {
                      'aria-label': `选择 ${String(row[rowKey])}`,
                      checked: selectedKeys.has(String(row[rowKey])),
                      disabled: rowSelection.getCheckboxProps?.(row).disabled,
                      onChange: (event: React.ChangeEvent<HTMLInputElement>) =>
                        toggleSelection(row, event.currentTarget.checked),
                      type: 'checkbox',
                    }),
                  )
                : null,
              tableColumns.map((column) =>
                React.createElement(
                  'td',
                  { key: String(column.key ?? column.dataIndex ?? column.title) },
                  column.render
                    ? column.render(column.dataIndex ? row[column.dataIndex] : undefined, row)
                    : String(column.dataIndex ? row[column.dataIndex] : ''),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  function StatisticCard({ statistic }: { statistic: Record<string, React.ReactNode> }) {
    return React.createElement(
      'section',
      null,
      statistic.prefix,
      React.createElement('h3', null, statistic.title),
      React.createElement('p', null, statistic.value),
      React.createElement('p', null, statistic.description),
    );
  }

  StatisticCard.Group = ({ children }: { children?: React.ReactNode }) =>
    React.createElement('section', null, children);

  function QueryFilter({
    children,
    'aria-label': ariaLabel,
    onFinish,
    onReset,
  }: {
    'aria-label'?: string;
    children?: React.ReactNode;
    onFinish?: (values: Record<string, FormDataEntryValue>) => void;
    onReset?: () => void;
  }) {
    return React.createElement(
      'form',
      {
        'aria-label': ariaLabel ?? '查询条件',
        onReset: () => onReset?.(),
        onSubmit: (event: React.FormEvent<HTMLFormElement>) => {
          event.preventDefault();
          onFinish?.(Object.fromEntries(new FormData(event.currentTarget)));
        },
      },
      children,
      React.createElement('button', { type: 'submit' }, '查询'),
      React.createElement('button', { type: 'reset' }, '重置'),
    );
  }

  function ProFormText({ label, name }: { label: React.ReactNode; name: string }) {
    return React.createElement(
      'label',
      null,
      label,
      React.createElement('input', { name, type: 'text' }),
    );
  }

  function ProFormSelect({
    label,
    name,
    options = [],
  }: {
    label: React.ReactNode;
    name: string;
    options?: Array<{ label: string; value: string }>;
  }) {
    return React.createElement(
      'label',
      null,
      label,
      React.createElement(
        'select',
        { name },
        React.createElement('option', { value: '' }, '全部'),
        options.map((option) =>
          React.createElement('option', { key: option.value, value: option.value }, option.label),
        ),
      ),
    );
  }

  return {
    PageContainer,
    ProCard,
    ProFormSelect,
    ProFormText,
    ProTable,
    QueryFilter,
    StatisticCard,
  };
});
