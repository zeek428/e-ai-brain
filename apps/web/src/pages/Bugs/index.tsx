import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { BugRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createManagementBug,
  deleteManagementBug,
  fetchProductContextOptions,
  fetchManagementBugs,
  updateManagementBug,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';

const severityLabels: Record<BugRecord['severity'], { color: string; label: string }> = {
  blocker: { color: 'red', label: '阻断' },
  critical: { color: 'volcano', label: '致命' },
  major: { color: 'orange', label: '严重' },
  minor: { color: 'blue', label: '一般' },
};

const statusLabels: Record<BugRecord['status'], { color: string; label: string }> = {
  assigned: { color: 'purple', label: '已分派' },
  closed: { color: 'default', label: '已关闭' },
  fixed: { color: 'cyan', label: '已修复' },
  needs_info: { color: 'gold', label: '待补充' },
  open: { color: 'red', label: '待处理' },
  reopened: { color: 'red', label: '重新打开' },
  triaged: { color: 'gold', label: '已分诊' },
  verified: { color: 'green', label: '已验证' },
};

const sourceLabels: Record<BugRecord['source'], { color: string; label: string }> = {
  ai_auto_test: { color: 'purple', label: 'AI 自动测试' },
  ai_post_release: { color: 'cyan', label: 'AI 上线后分析' },
  manual_test: { color: 'default', label: '人工登记' },
};

type BugFormValues = {
  assignee?: string;
  description: string;
  module_code?: string;
  product_id?: string;
  severity: BugRecord['severity'];
  source: BugRecord['source'];
  status?: BugRecord['status'];
  title: string;
  version_id?: string;
};

export default function BugsPage() {
  const [form] = Form.useForm<BugFormValues>();
  const [editingBug, setEditingBug] = useState<BugRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchManagementBugs);
  const {
    error: productContextError,
    rows: productContexts,
    status: productContextStatus,
  } = useRemoteRows(fetchProductContextOptions);
  const selectedProductId = Form.useWatch('product_id', form);
  const selectedProduct = useMemo(
    () => productContexts.find((product) => product.id === selectedProductId),
    [productContexts, selectedProductId],
  );
  const productOptions = useMemo(
    () =>
      productContexts.map((product) => ({
        label: `${product.code} · ${product.name}`,
        value: product.id,
      })),
    [productContexts],
  );
  const versionOptions = useMemo(
    () =>
      selectedProduct?.versions.map((version) => ({
        label: `${version.code} · ${version.name}`,
        value: version.id,
      })) ?? [],
    [selectedProduct],
  );

  const openCreateModal = () => {
    setEditingBug(null);
    form.resetFields();
    const firstProduct = productContexts[0];
    form.setFieldsValue({
      product_id: firstProduct?.id,
      severity: 'major',
      source: 'manual_test',
      version_id: firstProduct?.versions[0]?.id,
    });
    setIsModalOpen(true);
  };

  const handleProductChange = useCallback((productId: string) => {
    const product = productContexts.find((item) => item.id === productId);
    form.setFieldsValue({
      module_code: undefined,
      version_id: product?.versions[0]?.id,
    });
  }, [form, productContexts]);

  const openEditModal = useCallback((row: BugRecord) => {
    setEditingBug(row);
    form.setFieldsValue({
      assignee: row.assignee === '-' ? undefined : row.assignee,
      description: row.description ?? '',
      severity: row.severity,
      status: row.status,
      title: row.title,
    });
    setIsModalOpen(true);
  }, [form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    setIsSaving(true);
    try {
      if (editingBug) {
        await updateManagementBug(editingBug.id, {
          assignee: trimText(values.assignee),
          description: values.description.trim(),
          severity: values.severity,
          status: values.status,
          title: values.title.trim(),
        });
        message.success('Bug 已更新');
      } else {
        await createManagementBug({
          assignee: trimText(values.assignee),
          description: values.description.trim(),
          module_code: trimText(values.module_code),
          product_id: values.product_id?.trim(),
          severity: values.severity,
          source: values.source,
          title: values.title.trim(),
          version_id: trimText(values.version_id),
        });
        message.success('Bug 已登记');
      }
      setIsModalOpen(false);
      void reload();
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = useCallback(async (row: BugRecord) => {
    try {
      await deleteManagementBug(row.id);
      message.success('Bug 已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reload]);

  const columns = useMemo<ProColumns<BugRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        title: 'Bug 编号',
      },
      {
        dataIndex: 'title',
        title: 'Bug 标题',
      },
      {
        dataIndex: 'module',
        title: '所属模块',
      },
      {
        dataIndex: 'severity',
        title: '严重级别',
        render: (_, row) => {
          const severity = severityLabels[row.severity];
          return <StatusTag color={severity.color} label={severity.label} />;
        },
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) => {
          const statusLabel = statusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
      },
      {
        dataIndex: 'source',
        title: '来源',
        render: (_, row) => {
          const source = sourceLabels[row.source];
          return <StatusTag color={source.color} label={source.label} />;
        },
      },
      {
        dataIndex: 'assignee',
        title: '处理人',
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
            <Popconfirm okText="删除" onConfirm={() => handleDelete(row)} title={`删除 Bug ${row.id}？`}>
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDelete, openEditModal],
  );

  return (
    <>
      <ManagementListPage<BugRecord>
        breadcrumbGroup="需求交付"
        columns={columns}
        dataSource={dataSource}
        filters={[
          { label: 'Bug 标题', name: 'title', type: 'text' },
          { label: '所属模块', name: 'module', type: 'text' },
          {
            label: '严重级别',
            name: 'severity',
            options: [
              { label: '阻断', value: 'blocker' },
              { label: '致命', value: 'critical' },
              { label: '严重', value: 'major' },
              { label: '一般', value: 'minor' },
            ],
            type: 'select',
          },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '待处理', value: 'open' },
              { label: '待补充', value: 'needs_info' },
              { label: '已分诊', value: 'triaged' },
              { label: '已分派', value: 'assigned' },
              { label: '已修复', value: 'fixed' },
              { label: '已验证', value: 'verified' },
              { label: '已关闭', value: 'closed' },
              { label: '重新打开', value: 'reopened' },
            ],
            type: 'select',
          },
        ]}
        loading={status === 'loading'}
        notice={formatRemoteRowsError(error ?? productContextError)}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="登记 Bug"
        rowKey="id"
        tableTitle="Bug 列表"
        title="Bug 管理"
      />
      <Modal
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={() => setIsModalOpen(false)}
        onOk={() => void handleSave()}
        open={isModalOpen}
        title={editingBug ? '编辑 Bug' : '登记 Bug'}
      >
        <Form<BugFormValues> form={form} layout="vertical">
          <Form.Item label="Bug 标题" name="title" rules={[{ required: true, message: '请输入 Bug 标题' }]}>
            <Input />
          </Form.Item>
          {!editingBug ? (
            <>
              <Form.Item label="所属产品" name="product_id" rules={[{ required: true, message: '请选择产品' }]}>
                <Select
                  loading={productContextStatus === 'loading'}
                  onChange={handleProductChange}
                  optionFilterProp="label"
                  options={productOptions}
                  placeholder="请选择产品"
                  showSearch
                />
              </Form.Item>
              <Form.Item label="目标版本" name="version_id">
                <Select
                  allowClear
                  disabled={!selectedProduct || versionOptions.length === 0}
                  loading={productContextStatus === 'loading'}
                  options={versionOptions}
                  placeholder={selectedProduct ? '请选择版本，可留空' : '请先选择产品'}
                />
              </Form.Item>
              <Form.Item label="模块编码" name="module_code">
                <Input />
              </Form.Item>
              <Form.Item label="来源" name="source" rules={[{ required: true, message: '请选择来源' }]}>
                <Select
                  options={[
                    { label: '人工登记', value: 'manual_test' },
                    { label: 'AI 自动测试', value: 'ai_auto_test' },
                    { label: 'AI 上线后分析', value: 'ai_post_release' },
                  ]}
                />
              </Form.Item>
            </>
          ) : null}
          <Form.Item label="严重级别" name="severity" rules={[{ required: true, message: '请选择严重级别' }]}>
            <Select
              options={[
                { label: '阻断', value: 'blocker' },
                { label: '致命', value: 'critical' },
                { label: '严重', value: 'major' },
                { label: '一般', value: 'minor' },
              ]}
            />
          </Form.Item>
          {editingBug ? (
            <Form.Item label="状态" name="status">
              <Select
                options={[
                  { label: '待处理', value: 'open' },
                  { label: '待补充', value: 'needs_info' },
                  { label: '已分诊', value: 'triaged' },
                  { label: '已分派', value: 'assigned' },
                  { label: '已修复', value: 'fixed' },
                  { label: '已验证', value: 'verified' },
                  { label: '已关闭', value: 'closed' },
                  { label: '重新打开', value: 'reopened' },
                ]}
              />
            </Form.Item>
          ) : null}
          <Form.Item label="处理人" name="assignee">
            <Input />
          </Form.Item>
          <Form.Item label="描述" name="description" rules={[{ required: true, message: '请输入 Bug 描述' }]}>
            <Input.TextArea autoSize={{ minRows: 4 }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
