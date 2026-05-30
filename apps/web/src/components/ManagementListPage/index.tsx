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
  type: 'select' | 'text';
};

type ManagementListPageProps<Row extends Record<string, unknown>> = {
  breadcrumbGroup: string;
  columns: ProColumns<Row>[];
  dataSource: Row[];
  filters: FilterField[];
  notice?: ReactNode;
  primaryAction?: string;
  rowKey: keyof Row & string;
  tableTitle: string;
  title: string;
};

type FilterValues = Record<string, unknown>;

function normalizeFilterValue(value: unknown) {
  return String(value ?? '').trim();
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
  notice,
  primaryAction,
  rowKey,
  tableTitle,
  title,
}: ManagementListPageProps<Row>) {
  const [filterValues, setFilterValues] = useState<FilterValues>({});

  const proTableColumns = useMemo<ProColumns<Row>[]>(
    () => [
      ...filters.map<ProColumns<Row>>((field) => ({
        dataIndex: field.name,
        fieldProps: {
          placeholder:
            field.placeholder ?? (field.type === 'select' ? `请选择${field.label}` : `请输入${field.label}`),
        },
        hideInTable: true,
        title: field.label,
        valueEnum: field.type === 'select' ? toValueEnum(field.options) : undefined,
        valueType: field.type === 'select' ? 'select' : 'text',
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
      dataSource.filter((row) =>
        filters.every((field) => {
          const filterValue = normalizeFilterValue(filterValues[field.name]);

          if (!filterValue) {
            return true;
          }

          const rowValue = normalizeFilterValue(row[field.name as keyof Row]);

          if (field.type === 'select') {
            return rowValue === filterValue;
          }

          return rowValue.toLowerCase().includes(filterValue.toLowerCase());
        }),
      ),
    [dataSource, filterValues, filters],
  );

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
        onReset={() => setFilterValues({})}
        onSubmit={(values) => setFilterValues(values)}
        options={{
          density: true,
          fullScreen: true,
          reload: false,
          setting: true,
        }}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
        rowKey={rowKey}
        rowSelection={{}}
        search={{
          defaultCollapsed: false,
          labelWidth: 100,
        }}
        toolBarRender={() =>
          primaryAction
            ? [
                <Button icon={<PlusOutlined />} key="primary" type="primary">
                  {primaryAction}
                </Button>,
              ]
            : []
        }
      />
    </PageContainer>
  );
}

export function StatusTag({ color, label }: { color: string; label: string }) {
  return <Tag color={color}>{label}</Tag>;
}
