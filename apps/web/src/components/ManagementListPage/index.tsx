import { DeleteOutlined, PlusOutlined, SaveOutlined } from '@ant-design/icons';
import { PageContainer, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Input, Modal, Select, Space, Tag } from 'antd';
import type { TableProps } from 'antd';
import type { SorterResult, TableRowSelection } from 'antd/es/table/interface';
import { isValidElement, type ReactNode, useId, useMemo, useState } from 'react';

type FilterField = {
  label: string;
  name: string;
  options?: Array<{ label: string; value: string }>;
  placeholder?: string;
  type: 'dateRange' | 'select' | 'text';
};

type ManagementListPageProps<Row extends Record<string, unknown>> = {
  beforeTable?: ReactNode;
  breadcrumbGroup: string;
  columns: ProColumns<Row>[];
  dataSource: Row[];
  embedded?: boolean;
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
    performance?: ManagementListPerformance;
    total: number;
  };
  rowKey: keyof Row & string;
  rowSelection?: TableRowSelection<Row>;
  tableLayout?: TableProps<Row>['tableLayout'];
  tableScroll?: TableProps<Row>['scroll'];
  tableTitle: string;
  title: string;
  toolbarActions?: ReactNode[];
  viewStorageKey?: string;
};

export type FilterValues = Record<string, unknown>;

export type ManagementListQuery = {
  filters: FilterValues;
  page: number;
  pageSize: number;
  sortField?: string;
  sortOrder?: 'ascend' | 'descend';
};

export type ManagementListPerformance = {
  duration_ms?: number;
  p95_target_ms?: number;
  result_count?: number;
  slow?: boolean;
  slow_threshold_ms?: number;
  total?: number;
};

const DEFAULT_ACTION_COLUMN_WIDTH = 220;
const DEFAULT_DATA_COLUMN_WIDTH = 160;
const MIN_TABLE_SCROLL_X = 960;
const SAVED_FILTER_VIEW_STORAGE_PREFIX = 'ai-brain:management-list-filter-views:';

type SavedFilterView = {
  id: string;
  name: string;
  query: Pick<ManagementListQuery, 'filters' | 'sortField' | 'sortOrder'>;
  updatedAt: string;
};

function isActionColumn<Row extends Record<string, unknown>>(column: ProColumns<Row>) {
  return column.valueType === 'option' || column.key === 'actions' || column.title === '操作';
}

function defaultColumnWidth<Row extends Record<string, unknown>>(column: ProColumns<Row>) {
  return isActionColumn(column) ? DEFAULT_ACTION_COLUMN_WIDTH : DEFAULT_DATA_COLUMN_WIDTH;
}

type TableCellRenderResult = {
  children?: ReactNode;
  props: Record<string, unknown>;
};

function isTableCellRenderResult(value: unknown): value is TableCellRenderResult {
  return Boolean(
    value &&
      typeof value === 'object' &&
      !Array.isArray(value) &&
      !isValidElement(value) &&
      'children' in value &&
      'props' in value,
  );
}

function wrapRenderedCell<Row extends Record<string, unknown>>(column: ProColumns<Row>) {
  if (!column.render || isActionColumn(column)) {
    return column.render;
  }
  return (...renderArgs: Parameters<NonNullable<ProColumns<Row>['render']>>) => {
    const rendered = column.render?.(...renderArgs);
    if (isTableCellRenderResult(rendered)) {
      const cellResult: TableCellRenderResult = rendered;
      return {
        ...cellResult,
        children: <div className="management-table-cell">{cellResult.children}</div>,
      };
    }
    return <div className="management-table-cell">{rendered as ReactNode}</div>;
  };
}

function normalizeSorter<Row>(sorter: SorterResult<Row> | SorterResult<Row>[]) {
  const activeSorter = Array.isArray(sorter)
    ? sorter.find((item) => item.order)
    : sorter.order
      ? sorter
      : undefined;
  if (!activeSorter) {
    return {};
  }
  const field =
    typeof activeSorter.field === 'string'
      ? activeSorter.field
      : typeof activeSorter.columnKey === 'string'
        ? activeSorter.columnKey
        : undefined;
  return {
    sortField: field,
    sortOrder: activeSorter.order ?? undefined,
  };
}

function savedFilterViewStorageKey(viewStorageKey?: string) {
  return viewStorageKey ? `${SAVED_FILTER_VIEW_STORAGE_PREFIX}${viewStorageKey}` : undefined;
}

function readSavedFilterViews(viewStorageKey?: string): SavedFilterView[] {
  const storageKey = savedFilterViewStorageKey(viewStorageKey);
  if (!storageKey || typeof globalThis.localStorage === 'undefined') {
    return [];
  }
  try {
    const raw = globalThis.localStorage.getItem(storageKey);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .filter((item): item is SavedFilterView =>
        Boolean(
          item &&
            typeof item === 'object' &&
            typeof item.id === 'string' &&
            typeof item.name === 'string' &&
            item.query &&
            typeof item.query === 'object',
        ),
      )
      .map((item) => ({
        id: item.id,
        name: item.name,
        query: {
          filters:
            item.query.filters && typeof item.query.filters === 'object'
              ? item.query.filters
              : {},
          sortField: typeof item.query.sortField === 'string' ? item.query.sortField : undefined,
          sortOrder:
            item.query.sortOrder === 'ascend' || item.query.sortOrder === 'descend'
              ? item.query.sortOrder
              : undefined,
        },
        updatedAt: typeof item.updatedAt === 'string' ? item.updatedAt : '',
      }));
  } catch {
    return [];
  }
}

function writeSavedFilterViews(viewStorageKey: string | undefined, views: SavedFilterView[]) {
  const storageKey = savedFilterViewStorageKey(viewStorageKey);
  if (!storageKey || typeof globalThis.localStorage === 'undefined') {
    return;
  }
  try {
    globalThis.localStorage.setItem(storageKey, JSON.stringify(views));
  } catch {
    // Saved views are a local convenience; list operations must keep working if storage is unavailable.
  }
}

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

function formatDuration(value?: number) {
  return typeof value === 'number' && Number.isFinite(value) ? `${Math.max(0, value)}ms` : '-';
}

export function ManagementListPage<Row extends Record<string, unknown>>({
  beforeTable,
  breadcrumbGroup,
  columns,
  dataSource,
  embedded = false,
  filters,
  loading = false,
  notice,
  onPrimaryAction,
  onReload,
  primaryAction,
  remote,
  rowKey,
  rowSelection,
  tableLayout,
  tableScroll,
  tableTitle,
  title,
  toolbarActions = [],
  viewStorageKey,
}: ManagementListPageProps<Row>) {
  const savedFilterViewSelectId = `${useId()}-saved-filter-view`;
  const [filterValues, setFilterValues] = useState<FilterValues>({});
  const [sortState, setSortState] = useState<
    Pick<ManagementListQuery, 'sortField' | 'sortOrder'>
  >({});
  const [savedFilterViews, setSavedFilterViews] = useState<SavedFilterView[]>(() =>
    readSavedFilterViews(viewStorageKey),
  );
  const [selectedSavedViewId, setSelectedSavedViewId] = useState<string>();
  const [isSaveViewOpen, setIsSaveViewOpen] = useState(false);
  const [saveViewName, setSaveViewName] = useState('');
  const [tableFormVersion, setTableFormVersion] = useState(0);
  const resolvedTableLayout = tableLayout ?? 'fixed';
  const selectedSavedView = savedFilterViews.find((view) => view.id === selectedSavedViewId);
  const queryPerformance = remote?.performance;
  const isSlowListQuery = Boolean(queryPerformance?.slow);

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
        initialValue: filterValues[field.name],
        title: field.label,
        valueEnum: field.type === 'select' ? toValueEnum(field.options) : undefined,
        valueType:
          field.type === 'dateRange' ? 'dateRange' : field.type === 'select' ? 'select' : 'text',
      })),
      ...columns.map<ProColumns<Row>>((column) => ({
        ...column,
        ellipsis: column.ellipsis ?? (!column.render && !isActionColumn(column)),
        fixed: column.fixed ?? (isActionColumn(column) ? 'right' : undefined),
        render: wrapRenderedCell(column),
        search: false,
        width: column.width ?? defaultColumnWidth(column),
      })),
    ],
    [columns, filterValues, filters],
  );
  const resolvedTableScroll = useMemo<TableProps<Row>['scroll']>(() => {
    if (tableScroll) {
      return tableScroll;
    }
    const widthTotal = proTableColumns.reduce((total, column) => {
      if (column.hideInTable) {
        return total;
      }
      const width = column.width;
      if (typeof width === 'number') {
        return total + width;
      }
      if (typeof width === 'string') {
        const parsed = Number.parseInt(width, 10);
        return Number.isFinite(parsed) ? total + parsed : total + defaultColumnWidth(column);
      }
      return total + defaultColumnWidth(column);
    }, 0);
    return { x: Math.max(MIN_TABLE_SCROLL_X, widthTotal) };
  }, [proTableColumns, tableScroll]);

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
    setSortState({});
    setSelectedSavedViewId(undefined);
    setTableFormVersion((version) => version + 1);
    remote?.onChange({
      filters: {},
      page: 1,
      pageSize: remote.pageSize,
    });
  };

  const handleSubmit = (values: FilterValues) => {
    setFilterValues(values);
    setSelectedSavedViewId(undefined);
    remote?.onChange({
      filters: values,
      page: 1,
      pageSize: remote.pageSize,
      ...sortState,
    });
  };

  const handleApplySavedView = (viewId: string | undefined) => {
    setSelectedSavedViewId(viewId);
    if (!viewId) {
      return;
    }
    const view = savedFilterViews.find((item) => item.id === viewId);
    if (!view) {
      return;
    }
    const nextFilters = view.query.filters ?? {};
    const nextSortState = {
      sortField: view.query.sortField,
      sortOrder: view.query.sortOrder,
    };
    setFilterValues(nextFilters);
    setSortState(nextSortState);
    setTableFormVersion((version) => version + 1);
    remote?.onChange({
      filters: nextFilters,
      page: 1,
      pageSize: remote.pageSize,
      ...nextSortState,
    });
  };

  const openSaveViewModal = () => {
    setSaveViewName(
      selectedSavedView?.name || `筛选视图 ${savedFilterViews.length + 1}`,
    );
    setIsSaveViewOpen(true);
  };

  const saveCurrentView = () => {
    const now = new Date().toISOString();
    const viewId = selectedSavedViewId || `view_${Date.now()}`;
    const viewName = saveViewName.trim() || `筛选视图 ${savedFilterViews.length + 1}`;
    const nextView: SavedFilterView = {
      id: viewId,
      name: viewName,
      query: {
        filters: filterValues,
        ...sortState,
      },
      updatedAt: now,
    };
    const nextViews = selectedSavedViewId
      ? savedFilterViews.map((view) => (view.id === selectedSavedViewId ? nextView : view))
      : [...savedFilterViews, nextView];
    setSavedFilterViews(nextViews);
    setSelectedSavedViewId(viewId);
    writeSavedFilterViews(viewStorageKey, nextViews);
    setIsSaveViewOpen(false);
    setSaveViewName('');
  };

  const deleteSelectedView = () => {
    if (!selectedSavedViewId) {
      return;
    }
    const nextViews = savedFilterViews.filter((view) => view.id !== selectedSavedViewId);
    setSavedFilterViews(nextViews);
    setSelectedSavedViewId(undefined);
    writeSavedFilterViews(viewStorageKey, nextViews);
  };

  const savedFilterViewToolbar = viewStorageKey ? (
    <Space className="management-list-filter-views" key="saved-filter-views" wrap>
      <Select
        allowClear
        aria-label="筛选视图"
        id={savedFilterViewSelectId}
        onChange={handleApplySavedView}
        options={savedFilterViews.map((view) => ({
          label: view.name,
          value: view.id,
        }))}
        placeholder="筛选视图"
        style={{ minWidth: 160 }}
        value={selectedSavedViewId}
      />
      <Button aria-label="保存视图" icon={<SaveOutlined />} onClick={openSaveViewModal}>
        保存视图
      </Button>
      <Button
        aria-label="删除视图"
        disabled={!selectedSavedViewId}
        icon={<DeleteOutlined />}
        onClick={deleteSelectedView}
      >
        删除视图
      </Button>
    </Space>
  ) : null;
  const queryPerformanceToolbar =
    queryPerformance && queryPerformance.duration_ms !== undefined ? (
      <Tag color={isSlowListQuery ? 'orange' : 'default'} key="query-performance">
        查询 {formatDuration(queryPerformance.duration_ms)}
      </Tag>
    ) : null;

  const listContent = (
    <>
      {notice ? <Alert className="management-list-alert" showIcon title={notice} type="warning" /> : null}
      {isSlowListQuery ? (
        <Alert
          className="management-list-alert"
          description={`当前查询耗时 ${formatDuration(queryPerformance?.duration_ms)}，慢查询阈值 ${formatDuration(queryPerformance?.slow_threshold_ms ?? queryPerformance?.p95_target_ms)}。可结合接口 trace_id、筛选条件和数据库慢查询日志排查。`}
          showIcon
          title="列表查询较慢"
          type="warning"
        />
      ) : null}
      {beforeTable}
      <ProTable<Row>
        cardBordered
        className="management-list-table"
        columns={proTableColumns}
        dataSource={filteredDataSource}
        dateFormatter="string"
        headerTitle={tableTitle}
        key={tableFormVersion}
        loading={loading}
        onChange={(pagination, _tableFilters, sorter) => {
          if (!remote) {
            return;
          }
          const nextSortState = normalizeSorter(sorter);
          setSortState(nextSortState);
          setSelectedSavedViewId(undefined);
          remote.onChange({
            filters: filterValues,
            page: pagination.current ?? remote.page,
            pageSize: pagination.pageSize ?? remote.pageSize,
            ...nextSortState,
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
        rowSelection={rowSelection}
        scroll={resolvedTableScroll}
        search={{
          defaultCollapsed: false,
          labelWidth: 100,
        }}
        tableLayout={resolvedTableLayout}
        toolBarRender={() => [
          ...(savedFilterViewToolbar ? [savedFilterViewToolbar] : []),
          ...(queryPerformanceToolbar ? [queryPerformanceToolbar] : []),
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
      {viewStorageKey ? (
        <Modal
          okButtonProps={{ 'aria-label': '保存筛选视图' }}
          okText="保存"
          onCancel={() => setIsSaveViewOpen(false)}
          onOk={saveCurrentView}
          open={isSaveViewOpen}
          title={selectedSavedView ? '更新筛选视图' : '保存筛选视图'}
        >
          <Input
            aria-label="筛选视图名称"
            onChange={(event) => setSaveViewName(event.currentTarget.value)}
            onPressEnter={saveCurrentView}
            placeholder="请输入筛选视图名称"
            value={saveViewName}
          />
        </Modal>
      ) : null}
    </>
  );

  if (embedded) {
    return listContent;
  }

  return (
    <PageContainer
      breadcrumb={{
        items: [{ title: breadcrumbGroup }, { title }],
      }}
      title={false}
    >
      {listContent}
    </PageContainer>
  );
}

export function StatusTag({ color, label }: { color: string; label: string }) {
  return <Tag color={color}>{label}</Tag>;
}
