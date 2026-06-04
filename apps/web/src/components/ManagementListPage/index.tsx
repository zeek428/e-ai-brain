import { PlusOutlined } from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Tag } from 'antd';
import { type ReactNode, useMemo, useState } from 'react';

type FilterField = {
  label: string;
  name: string;
  options?: Array<{ label: string; value: string }>;
  placeholder?: string;
  type: 'dateRange' | 'select' | 'text';
};

type ManagementListPageProps<Row extends Record<string, unknown>> = {
  breadcrumbGroup: string;
  columns: ProColumns<Row>[];
  dataSource: Row[];
  filters: FilterField[];
  loading?: boolean;
  notice?: ReactNode;
  onPrimaryAction?: () => void;
  onReload?: () => void;
  primaryAction?: string;
  remote?: {
    onChange: (query: ManagementListQuery) => void;
    page: number;
    pageSize: number;
    total: number;
  };
  rowKey: keyof Row & string;
  tableTitle: string;
  title: string;
  toolbarActions?: ReactNode[];
};

export type FilterValues = Record<string, unknown>;

export type ManagementListQuery = {
  filters: FilterValues;
  page: number;
  pageSize: number;
};

function normalizeFilterValue(value: unknown) {
  return String(value ?? '').trim();
}

function normalizeDateRangeValue(value: unknown) {
  if (Array.isArray(value)) {
    return [normalizeFilterValue(value[0]), normalizeFilterValue(value[1])] as const;
  }
  const [start = '', end = ''] = normalizeFilterValue(value).split(',');
  return [start.trim(), end.trim()] as const;
}

function parseDateBoundary(value: string, boundary: 'end' | 'start') {
  if (!value) {
    return undefined;
  }
  const dateOnlyMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnlyMatch) {
    const [, year, month, day] = dateOnlyMatch;
    const parsed = new Date(Number(year), Number(month) - 1, Number(day));
    if (boundary === 'end') {
      parsed.setHours(23, 59, 59, 999);
    }
    return parsed.getTime();
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return undefined;
  }
  return parsed.getTime();
}

function isWithinDateRange(rowValue: unknown, filterValue: unknown) {
  const [startValue, endValue] = normalizeDateRangeValue(filterValue);
  if (!startValue && !endValue) {
    return true;
  }
  const rowTime = parseDateBoundary(normalizeFilterValue(rowValue), 'start');
  if (rowTime === undefined) {
    return false;
  }
  const startTime = parseDateBoundary(startValue, 'start');
  const endTime = parseDateBoundary(endValue, 'end');
  if (startTime !== undefined && rowTime < startTime) {
    return false;
  }
  if (endTime !== undefined && rowTime > endTime) {
    return false;
  }
  return true;
}

function toValueEnum(options?: Array<{ label: string; value: string }>) {
  return options?.reduce<Record<string, { text: string }>>((valueEnum, option) => {
    valueEnum[option.value] = { text: option.label };
    return valueEnum;
  }, {});
}

export function ManagementListPage<Row extends Record<string, unknown>>({
  breadcrumbGroup,
  columns,
  dataSource,
  filters,
  loading = false,
  notice,
  onPrimaryAction,
  onReload,
  primaryAction,
  remote,
  rowKey,
  tableTitle,
  title,
  toolbarActions = [],
}: ManagementListPageProps<Row>) {
  const [filterValues, setFilterValues] = useState<FilterValues>({});

  const proTableColumns = useMemo<ProColumns<Row>[]>(
    () => [
      ...filters.map<ProColumns<Row>>((field) => ({
        dataIndex: field.name,
        fieldProps: {
          placeholder:
            field.placeholder ??
            (field.type === 'dateRange'
              ? ['开始时间', '结束时间']
              : field.type === 'select'
                ? `请选择${field.label}`
                : `请输入${field.label}`),
        },
        hideInTable: true,
        title: field.label,
        valueEnum: field.type === 'select' ? toValueEnum(field.options) : undefined,
        valueType:
          field.type === 'dateRange' ? 'dateRange' : field.type === 'select' ? 'select' : 'text',
      })),
      ...columns.map<ProColumns<Row>>((column) => ({
        ...column,
        search: false,
      })),
    ],
    [columns, filters],
  );

  const filteredDataSource = useMemo(
    () =>
      remote
        ? dataSource
        : dataSource.filter((row) =>
            filters.every((field) => {
              const filterValue = normalizeFilterValue(filterValues[field.name]);

              if (!filterValue) {
                return true;
              }

              const rowValue = normalizeFilterValue(row[field.name as keyof Row]);

              if (field.type === 'dateRange') {
                return isWithinDateRange(row[field.name as keyof Row], filterValues[field.name]);
              }

              if (field.type === 'select') {
                return rowValue === filterValue;
              }

              return rowValue.toLowerCase().includes(filterValue.toLowerCase());
            }),
          ),
    [dataSource, filterValues, filters, remote],
  );

  const handleReset = () => {
    setFilterValues({});
    remote?.onChange({
      filters: {},
      page: 1,
      pageSize: remote.pageSize,
    });
  };

  const handleSubmit = (values: FilterValues) => {
    setFilterValues(values);
    remote?.onChange({
      filters: values,
      page: 1,
      pageSize: remote.pageSize,
    });
  };

  return (
    <PageContainer
      breadcrumb={{
        items: [{ title: breadcrumbGroup }, { title }],
      }}
      title={false}
    >
      {notice ? <Alert className="management-list-alert" showIcon title={notice} type="warning" /> : null}
      <ProTable<Row>
        cardBordered
        columns={proTableColumns}
        dataSource={filteredDataSource}
        dateFormatter="string"
        headerTitle={tableTitle}
        loading={loading}
        onChange={(pagination) => {
          if (!remote) {
            return;
          }
          remote.onChange({
            filters: filterValues,
            page: pagination.current ?? remote.page,
            pageSize: pagination.pageSize ?? remote.pageSize,
          });
        }}
        onReset={handleReset}
        onSubmit={handleSubmit}
        options={{
          density: true,
          fullScreen: true,
          reload: onReload ? () => onReload() : false,
          setting: true,
        }}
        pagination={{
          current: remote?.page,
          pageSize: remote?.pageSize ?? 10,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
          total: remote?.total,
        }}
        rowKey={rowKey}
        rowSelection={{}}
        search={{
          defaultCollapsed: false,
          labelWidth: 100,
        }}
        toolBarRender={() => [
          ...toolbarActions,
          ...(primaryAction
            ? [
                <Button
                  aria-label={primaryAction}
                  icon={<PlusOutlined />}
                  key="primary"
                  onClick={onPrimaryAction}
                  type="primary"
                >
                  {primaryAction}
                </Button>,
              ]
            : []),
        ]}
      />
    </PageContainer>
  );
}

export function StatusTag({ color, label }: { color: string; label: string }) {
  return <Tag color={color}>{label}</Tag>;
}
