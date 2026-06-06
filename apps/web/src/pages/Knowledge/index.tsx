import { DeleteOutlined, EditOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, InputNumber, Modal, Popconfirm, Select, Space, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { KnowledgeRecord } from '../../data/management';
import { type UserRoleDefinition, toUserRoleOptions } from '../../data/roles';
import { formatRemoteRowsError, normalizeRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  approveKnowledgeDeposit,
  createManagementKnowledgeDocument,
  deleteManagementKnowledgeDocument,
  fetchKnowledgeDeposits,
  fetchKnowledgeSearchResults,
  fetchManagementKnowledgeList,
  fetchRoleDefinitions,
  rejectKnowledgeDeposit,
  retryKnowledgeDocumentIndex,
  updateManagementKnowledgeDocument,
  type KnowledgeListQuery,
  type KnowledgeDepositRecord,
  type KnowledgeSearchResultRecord,
} from '../../services/aiBrain';
import { formatMutationError, joinTextList, splitCommaText } from '../../utils/managementCrud';

const { Text } = Typography;

const statusLabels: Record<KnowledgeRecord['status'], { color: string; label: string }> = {
  archived: { color: 'default', label: '已归档' },
  importing: { color: 'blue', label: '索引中' },
  indexed: { color: 'green', label: '已索引' },
  index_failed: { color: 'red', label: '索引失败' },
  pending_index: { color: 'gold', label: '待索引' },
  text_indexed: { color: 'cyan', label: '文本索引' },
  vector_indexed: { color: 'green', label: '向量索引' },
};

const depositStatusLabels: Record<string, { color: string; label: string }> = {
  approved: { color: 'green', label: '已入库' },
  pending: { color: 'gold', label: '待审核' },
  rejected: { color: 'red', label: '已拒绝' },
};

type KnowledgeFormValues = {
  content: string;
  doc_type: string;
  index_status?: KnowledgeRecord['status'];
  permission_roles?: string[];
  tags?: string;
  title: string;
};

type RejectDepositFormValues = {
  reason: string;
};

type KnowledgeSearchFormValues = {
  query: string;
  top_k?: number;
};

const knowledgeSortFieldMap: Record<string, string> = {
  documentType: 'doc_type',
  id: 'id',
  ownerRole: 'permission_roles',
  status: 'index_status',
  title: 'title',
  updatedAt: 'updated_at',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

function buildKnowledgeListQuery(query: ManagementListQuery): KnowledgeListQuery {
  return {
    documentType: normalizeFilterText(query.filters.documentType),
    keyword: normalizeFilterText(query.filters.title),
    ownerRole: normalizeFilterText(query.filters.ownerRole),
    page: query.page,
    pageSize: query.pageSize,
    sortField: query.sortField ? knowledgeSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
  };
}

export default function KnowledgePage() {
  const [form] = Form.useForm<KnowledgeFormValues>();
  const [rejectDepositForm] = Form.useForm<RejectDepositFormValues>();
  const [searchForm] = Form.useForm<KnowledgeSearchFormValues>();
  const [depositRows, setDepositRows] = useState<KnowledgeDepositRecord[]>([]);
  const [depositsLoading, setDepositsLoading] = useState(false);
  const [isDepositsModalOpen, setIsDepositsModalOpen] = useState(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [editingDocument, setEditingDocument] = useState<KnowledgeRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [rejectingDeposit, setRejectingDeposit] = useState<KnowledgeDepositRecord | null>(null);
  const [searchRows, setSearchRows] = useState<KnowledgeSearchResultRecord[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [roleCatalogError, setRoleCatalogError] = useState<string | undefined>();
  const [roleDefinitions, setRoleDefinitions] = useState<UserRoleDefinition[]>([]);
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'updatedAt',
    sortOrder: 'descend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    rows: KnowledgeRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const roleOptions = useMemo(() => toUserRoleOptions(roleDefinitions), [roleDefinitions]);

  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchManagementKnowledgeList(buildKnowledgeListQuery(listQuery));
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
    } catch (loadError: unknown) {
      setListState((current) => ({
        ...current,
        error: normalizeRemoteRowsError(loadError),
        rows: [],
        status: 'error',
      }));
    }
  }, [listQuery]);

  useEffect(() => {
    let isCurrent = true;

    fetchRoleDefinitions()
      .then((definitions) => {
        if (isCurrent) {
          setRoleDefinitions(definitions);
          setRoleCatalogError(undefined);
        }
      })
      .catch((roleError: unknown) => {
        if (isCurrent) {
          setRoleDefinitions([]);
          setRoleCatalogError(`角色目录加载失败：${formatMutationError(roleError)}`);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchManagementKnowledgeList(buildKnowledgeListQuery(listQuery))
      .then((result) => {
        if (isCurrent) {
          setListState({
            page: result.page,
            pageSize: result.pageSize,
            rows: result.rows,
            status: 'ready',
            total: result.total,
          });
        }
      })
      .catch((loadError: unknown) => {
        if (isCurrent) {
          setListState((current) => ({
            ...current,
            error: normalizeRemoteRowsError(loadError),
            rows: [],
            status: 'error',
          }));
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [listQuery]);

  const openCreateModal = () => {
    setEditingDocument(null);
    form.resetFields();
    form.setFieldsValue({
      doc_type: 'manual',
      permission_roles: ['admin'],
    });
    setIsModalOpen(true);
  };

  const reloadDeposits = useCallback(async () => {
    setDepositsLoading(true);
    try {
      const deposits = await fetchKnowledgeDeposits('pending');
      setDepositRows(deposits);
    } catch (depositError) {
      message.error(formatMutationError(depositError));
    } finally {
      setDepositsLoading(false);
    }
  }, []);

  const openDepositsModal = useCallback(() => {
    setIsDepositsModalOpen(true);
    void reloadDeposits();
  }, [reloadDeposits]);

  const openSearchModal = useCallback(() => {
    searchForm.setFieldsValue({ top_k: 5 });
    setSearchRows([]);
    setHasSearched(false);
    setIsSearchModalOpen(true);
  }, [searchForm]);

  const openEditModal = useCallback((row: KnowledgeRecord) => {
    setEditingDocument(row);
    form.setFieldsValue({
      content: row.content ?? '',
      doc_type: row.documentType,
      index_status: row.status,
      permission_roles: row.permissionRoles?.length
        ? row.permissionRoles
        : splitCommaText(row.ownerRole),
      tags: joinTextList(row.tags),
      title: row.title,
    });
    setIsModalOpen(true);
  }, [form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    const payload = {
      content: values.content.trim(),
      doc_type: values.doc_type.trim(),
      index_status: editingDocument ? values.index_status : undefined,
      permission_roles: values.permission_roles ?? [],
      tags: splitCommaText(values.tags),
      title: values.title.trim(),
    };

    setIsSaving(true);
    try {
      if (editingDocument) {
        await updateManagementKnowledgeDocument(editingDocument.id, payload);
        message.success('知识文档已更新');
      } else {
        await createManagementKnowledgeDocument(payload);
        message.success('知识文档已导入');
      }
      setIsModalOpen(false);
      void reload();
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = useCallback(async (row: KnowledgeRecord) => {
    try {
      await deleteManagementKnowledgeDocument(row.id);
      message.success('知识文档已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reload]);

  const handleRetryIndex = useCallback(async (row: KnowledgeRecord) => {
    try {
      await retryKnowledgeDocumentIndex(row.id);
      message.success('知识索引已重试');
      await reload();
    } catch (retryError) {
      message.error(formatMutationError(retryError));
    }
  }, [reload]);

  const handleApproveDeposit = useCallback(async (row: KnowledgeDepositRecord) => {
    try {
      await approveKnowledgeDeposit(row.id, {
        permissionRoles: ['admin'],
        title: row.title,
      });
      message.success('知识沉淀已入库');
      await Promise.all([reloadDeposits(), reload()]);
    } catch (depositError) {
      message.error(formatMutationError(depositError));
    }
  }, [reload, reloadDeposits]);

  const openRejectDepositModal = useCallback((row: KnowledgeDepositRecord) => {
    setRejectingDeposit(row);
    rejectDepositForm.resetFields();
  }, [rejectDepositForm]);

  const handleRejectDeposit = async () => {
    if (!rejectingDeposit) {
      return;
    }
    const values = await rejectDepositForm.validateFields();
    try {
      await rejectKnowledgeDeposit(rejectingDeposit.id, values.reason.trim());
      message.success('知识沉淀已拒绝');
      setRejectingDeposit(null);
      await reloadDeposits();
    } catch (depositError) {
      message.error(formatMutationError(depositError));
    }
  };

  const handleSearch = async () => {
    const values = await searchForm.validateFields();
    setSearchLoading(true);
    try {
      const results = await fetchKnowledgeSearchResults(values.query.trim(), values.top_k ?? 5);
      setSearchRows(results);
      setHasSearched(true);
    } catch (searchError) {
      message.error(formatMutationError(searchError));
    } finally {
      setSearchLoading(false);
    }
  };

  const columns = useMemo<ProColumns<KnowledgeRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        sorter: true,
        title: '知识编号',
      },
      {
        dataIndex: 'title',
        sorter: true,
        title: '知识标题',
      },
      {
        dataIndex: 'documentType',
        sorter: true,
        title: '类型',
      },
      {
        dataIndex: 'ownerRole',
        sorter: true,
        title: '权限角色',
      },
      {
        dataIndex: 'status',
        sorter: true,
        title: '状态',
        render: (_, row) => {
          const statusLabel = statusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
      },
      {
        dataIndex: 'indexError',
        title: '索引错误',
        render: (_, row) => row.indexError || row.vectorIndexError || '-',
      },
      {
        dataIndex: 'updatedAt',
        sorter: true,
        title: '更新时间',
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button icon={<EditOutlined />} onClick={() => openEditModal(row)} type="link">
              编辑
            </Button>
            {row.status === 'index_failed' || row.status === 'text_indexed' ? (
              <Button icon={<ReloadOutlined />} onClick={() => handleRetryIndex(row)} type="link">
                {row.status === 'text_indexed' ? '补向量索引' : '重试索引'}
              </Button>
            ) : null}
            <Popconfirm okText="删除" onConfirm={() => handleDelete(row)} title={`删除知识 ${row.id}？`}>
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDelete, handleRetryIndex, openEditModal],
  );

  const depositColumns = useMemo<ProColumns<KnowledgeDepositRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        title: '沉淀编号',
      },
      {
        dataIndex: 'title',
        title: '沉淀标题',
      },
      {
        dataIndex: 'aiTaskId',
        title: '任务编号',
      },
      {
        dataIndex: 'content',
        title: '内容摘要',
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) => {
          const label = depositStatusLabels[row.status] ?? { color: 'default', label: row.status };
          return <StatusTag color={label.color} label={label.label} />;
        },
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) =>
          row.status === 'pending' ? (
            <Space size={4}>
              <Button onClick={() => handleApproveDeposit(row)} type="link">
                批准入库
              </Button>
              <Button danger onClick={() => openRejectDepositModal(row)} type="link">
                拒绝
              </Button>
            </Space>
          ) : null,
      },
    ],
    [handleApproveDeposit, openRejectDepositModal],
  );

  const searchColumns = useMemo<ProColumns<KnowledgeSearchResultRecord>[]>(
    () => [
      {
        dataIndex: 'title',
        title: '知识标题',
      },
      {
        dataIndex: 'sourceLabel',
        title: '来源',
      },
      {
        dataIndex: 'retrievalMode',
        title: '召回模式',
        render: (_, row) => (row.retrievalMode === 'vector' ? '向量' : '关键词'),
      },
      {
        dataIndex: 'content',
        title: '内容摘要',
      },
    ],
    [],
  );

  return (
    <>
      <ManagementListPage<KnowledgeRecord>
        breadcrumbGroup="产品资产"
        columns={columns}
        dataSource={listState.rows}
        filters={[
          { label: '知识标题', name: 'title', type: 'text' },
          {
            label: '类型',
            name: 'documentType',
            options: [
              { label: 'PRD', value: 'PRD' },
              { label: 'Spec', value: 'Spec' },
              { label: 'Deposit', value: 'Deposit' },
              { label: 'Manual', value: 'manual' },
            ],
            type: 'select',
          },
          { label: '权限角色', name: 'ownerRole', type: 'text' },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '已索引', value: 'indexed' },
              { label: '文本索引', value: 'text_indexed' },
              { label: '向量索引', value: 'vector_indexed' },
              { label: '待索引', value: 'pending_index' },
              { label: '索引中', value: 'importing' },
              { label: '索引失败', value: 'index_failed' },
              { label: '已归档', value: 'archived' },
            ],
            type: 'select',
          },
        ]}
        loading={listState.status === 'loading'}
        notice={formatRemoteRowsError(listState.error) ?? roleCatalogError}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="导入文档"
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          total: listState.total,
        }}
        rowKey="id"
        tableTitle="知识列表"
        title="知识中心"
        toolbarActions={[
          <Button aria-label="知识检索" icon={<SearchOutlined />} key="knowledge-search" onClick={openSearchModal}>
            知识检索
          </Button>,
          <Button key="deposit-review" onClick={openDepositsModal}>
            沉淀审核
          </Button>,
        ]}
      />
      <Modal
        footer={null}
        onCancel={() => setIsSearchModalOpen(false)}
        open={isSearchModalOpen}
        title="知识检索"
        width={860}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Form<KnowledgeSearchFormValues> form={searchForm} layout="inline">
            <Form.Item
              label="检索关键词"
              name="query"
              rules={[{ required: true, message: '请输入检索关键词' }]}
            >
              <Input aria-label="检索关键词" placeholder="输入需求、技术方案或规则关键词" />
            </Form.Item>
            <Form.Item label="返回条数" name="top_k">
              <InputNumber min={1} max={20} precision={0} />
            </Form.Item>
            <Form.Item>
              <Button
                aria-label="检索"
                loading={searchLoading}
                onClick={() => void handleSearch()}
                type="primary"
              >
                检索
              </Button>
            </Form.Item>
          </Form>
          <ProTable<KnowledgeSearchResultRecord>
            columns={searchColumns}
            dataSource={searchRows}
            loading={searchLoading}
            options={false}
            pagination={false}
            rowKey="id"
            search={false}
          />
          {hasSearched && searchRows.length === 0 && !searchLoading ? (
            <Text type="secondary">没有检索到可访问的知识结果。</Text>
          ) : null}
        </Space>
      </Modal>
      <Modal
        footer={null}
        onCancel={() => setIsDepositsModalOpen(false)}
        open={isDepositsModalOpen}
        title="沉淀审核"
        width={920}
      >
        <ProTable<KnowledgeDepositRecord>
          columns={depositColumns}
          dataSource={depositRows}
          loading={depositsLoading}
          options={false}
          pagination={false}
          rowKey="id"
          search={false}
        />
        {depositRows.length === 0 && !depositsLoading ? (
          <Text type="secondary">当前没有待审核知识沉淀。</Text>
        ) : null}
      </Modal>
      <Modal
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={() => setIsModalOpen(false)}
        onOk={() => void handleSave()}
        open={isModalOpen}
        title={editingDocument ? '编辑知识文档' : '导入知识文档'}
      >
        <Form<KnowledgeFormValues> form={form} layout="vertical">
          <Form.Item label="知识标题" name="title" rules={[{ required: true, message: '请输入知识标题' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="类型" name="doc_type" rules={[{ required: true, message: '请输入知识类型' }]}>
            <Input placeholder="manual / PRD / Spec / Deposit" />
          </Form.Item>
          <Form.Item label="权限角色" name="permission_roles" rules={[{ required: true, message: '请选择权限角色' }]}>
            <Select
              disabled={roleOptions.length === 0}
              mode="multiple"
              optionFilterProp="label"
              options={roleOptions}
              placeholder="请选择权限角色"
            />
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Input />
          </Form.Item>
          {editingDocument ? (
            <Form.Item label="索引状态" name="index_status">
              <Select
                options={[
                  { label: '已索引', value: 'indexed' },
                  { label: '文本索引', value: 'text_indexed' },
                  { label: '向量索引', value: 'vector_indexed' },
                  { label: '待索引', value: 'pending_index' },
                  { label: '索引中', value: 'importing' },
                  { label: '索引失败', value: 'index_failed' },
                  { label: '已归档', value: 'archived' },
                ]}
              />
            </Form.Item>
          ) : null}
          <Form.Item label="内容" name="content" rules={[{ required: true, message: '请输入知识内容' }]}>
            <Input.TextArea rows={5} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        onCancel={() => setRejectingDeposit(null)}
        onOk={() => void handleRejectDeposit()}
        open={Boolean(rejectingDeposit)}
        title={rejectingDeposit ? `拒绝沉淀：${rejectingDeposit.title}` : '拒绝沉淀'}
      >
        <Form<RejectDepositFormValues> form={rejectDepositForm} layout="vertical">
          <Form.Item label="拒绝原因" name="reason" rules={[{ required: true, message: '请输入拒绝原因' }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
