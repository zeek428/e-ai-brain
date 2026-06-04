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
  duplicate_of_bug_id?: string;
  evidence_json?: string;
  module_code?: string;
  product_id?: string;
  related_task_id?: string;
  reproduce_steps_text?: string;
  requirement_id?: string;
  severity: BugRecord['severity'];
  source: BugRecord['source'];
  status?: BugRecord['status'];
  title: string;
  version_id?: string;
};

function formatEvidenceJson(evidence?: Record<string, unknown>) {
  if (!evidence || Object.keys(evidence).length === 0) {
    return '';
  }
  return JSON.stringify(evidence, null, 2);
}

function parseEvidenceJson(value?: string): Record<string, unknown> {
  const trimmed = value?.trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('证据 JSON 请输入对象 JSON');
  }
  return parsed as Record<string, unknown>;
}

function evidenceJsonRule() {
  return {
    validator(_: unknown, value?: string) {
      try {
        parseEvidenceJson(value);
        return Promise.resolve();
      } catch {
        return Promise.reject(new Error('证据 JSON 请输入合法对象 JSON'));
      }
    },
  };
}

function formatReproduceSteps(steps?: string[]) {
  return steps?.join('\n') ?? '';
}

function parseReproduceSteps(value?: string) {
  return (value ?? '')
    .split(/\r?\n/)
    .map((step) => step.trim())
    .filter(Boolean);
}

function isFormValidationError(error: unknown) {
  return Boolean(
    error &&
      typeof error === 'object' &&
      'errorFields' in error &&
      Array.isArray((error as { errorFields?: unknown }).errorFields),
  );
}

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
  const duplicateBugOptions = useMemo(
    () => {
      const duplicateProductId = editingBug?.productId ?? selectedProductId;
      return dataSource
        .filter(
          (bug) =>
            bug.id !== editingBug?.id &&
            (!duplicateProductId || bug.productId === duplicateProductId),
        )
        .map((bug) => ({
          label: `${bug.id} · ${bug.title}`,
          value: bug.id,
        }));
    },
    [dataSource, editingBug?.id, editingBug?.productId, selectedProductId],
  );

  const openCreateModal = () => {
    setEditingBug(null);
    form.resetFields();
    const firstProduct = productContexts[0];
    form.setFieldsValue({
      duplicate_of_bug_id: undefined,
      evidence_json: '',
      product_id: firstProduct?.id,
      reproduce_steps_text: '',
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

  const handleDuplicateChange = useCallback((bugId?: string) => {
    if (bugId && editingBug) {
      form.setFieldsValue({ status: 'closed' });
    }
  }, [editingBug, form]);

  const openEditModal = useCallback((row: BugRecord) => {
    setEditingBug(row);
    form.resetFields();
    form.setFieldsValue({
      assignee: row.assignee === '-' ? undefined : row.assignee,
      description: row.description ?? '',
      duplicate_of_bug_id: row.duplicateOfBugId,
      evidence_json: formatEvidenceJson(row.evidence),
      reproduce_steps_text: formatReproduceSteps(row.reproduceSteps),
      severity: row.severity,
      status: row.status,
      title: row.title,
    });
    setIsModalOpen(true);
  }, [form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      const duplicateOfBugId = trimText(values.duplicate_of_bug_id);
      const evidence = parseEvidenceJson(values.evidence_json);
      const reproduceSteps = parseReproduceSteps(values.reproduce_steps_text);
      setIsSaving(true);
      if (editingBug) {
        await updateManagementBug(editingBug.id, {
          assignee: trimText(values.assignee),
          description: values.description.trim(),
          duplicate_of_bug_id: duplicateOfBugId ?? null,
          evidence,
          reproduce_steps: reproduceSteps,
          severity: values.severity,
          status: values.status,
          title: values.title.trim(),
        });
        message.success('Bug 已更新');
      } else {
        await createManagementBug({
          assignee: trimText(values.assignee),
          description: values.description.trim(),
          duplicate_of_bug_id: duplicateOfBugId,
          evidence,
          module_code: trimText(values.module_code),
          product_id: values.product_id?.trim(),
          related_task_id: trimText(values.related_task_id),
          reproduce_steps: reproduceSteps,
          requirement_id: trimText(values.requirement_id),
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
      if (isFormValidationError(saveError)) {
        return;
      }
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
        dataIndex: 'versionName',
        title: '迭代版本',
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
          { label: '迭代版本', name: 'versionName', type: 'text' },
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
        cancelText="取消"
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={() => setIsModalOpen(false)}
        okText="保存"
        onOk={handleSave}
        open={isModalOpen}
        title={editingBug ? '编辑 Bug' : '登记 Bug'}
        width={680}
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
              <Form.Item label="关联需求 ID" name="requirement_id">
                <Input />
              </Form.Item>
              <Form.Item label="关联任务 ID" name="related_task_id">
                <Input />
              </Form.Item>
            </>
          ) : (
            <Form.Item label="来源">
              <Input aria-label="来源" disabled value={sourceLabels[editingBug.source].label} />
            </Form.Item>
          )}
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
          <Form.Item label="重复归并" name="duplicate_of_bug_id">
            <Select
              allowClear
              disabled={duplicateBugOptions.length === 0}
              onChange={handleDuplicateChange}
              optionFilterProp="label"
              options={duplicateBugOptions}
              placeholder={duplicateBugOptions.length === 0 ? '暂无可归并 Bug' : '选择主 Bug，可留空'}
              showSearch
            />
          </Form.Item>
          <Form.Item label="处理人" name="assignee">
            <Input />
          </Form.Item>
          <Form.Item label="描述" name="description" rules={[{ required: true, message: '请输入 Bug 描述' }]}>
            <Input.TextArea autoSize={{ minRows: 4 }} />
          </Form.Item>
          <Form.Item label="复现步骤" name="reproduce_steps_text">
            <Input.TextArea autoSize={{ minRows: 3 }} />
          </Form.Item>
          <Form.Item label="证据 JSON" name="evidence_json" rules={[evidenceJsonRule()]}>
            <Input.TextArea autoSize={{ minRows: 3 }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
