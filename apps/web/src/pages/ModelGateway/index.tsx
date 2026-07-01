import { DeleteOutlined, EditOutlined, ExperimentOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import type { ColumnsType } from 'antd/es/table';
import {
  Alert,
  AutoComplete,
  Button,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Radio,
  Select,
  Space,
  Switch,
  Tag,
  Table,
  Typography,
  message,
} from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { ExecutionTraceLink } from '../../components/ExecutionTraceLink';
import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { ModelGatewayConfigRecord } from '../../data/management';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';
import {
  createModelGatewayConfig,
  deleteModelGatewayConfig,
  fetchModelGatewayConfigList,
  fetchModelGatewayLogs,
  testModelGatewayConfig,
  updateModelGatewayConfig,
  type ModelGatewayConfigTestResult,
  type ModelGatewayLogQuery,
  type ModelGatewayLogRecord,
  type RemoteListPerformance,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { formatMutationError, trimText } from '../../utils/managementCrud';
import {
  TEST_TARGET_FIELDS,
  buildModelGatewayListQuery,
  chatModelOptions,
  embeddingModeLabels,
  embeddingModelOptions,
  formatDuration,
  formatTestStatus,
  formatTokenSummary,
  resolveModelGatewayLogSorter,
  type ModelGatewayFormValues,
} from './modelGatewayPageHelpers';

export default function ModelGatewayPage() {
  const [form] = Form.useForm<ModelGatewayFormValues>();
  const embeddingMode = Form.useWatch('embedding_connection_mode', form) ?? 'disabled';
  const [editingConfig, setEditingConfig] = useState<ModelGatewayConfigRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testingConfigId, setTestingConfigId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<ModelGatewayConfigTestResult | null>(null);
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'name',
    sortOrder: 'ascend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: ModelGatewayConfigRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const [logQuery, setLogQuery] = useState<ModelGatewayLogQuery>({
    page: 1,
    pageSize: 5,
    sortField: 'created_at',
    sortOrder: 'descend',
  });
  const [logState, setLogState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: ModelGatewayLogRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 5,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchModelGatewayConfigList(buildModelGatewayListQuery(listQuery));
      setListState({
        page: result.page,
        pageSize: result.pageSize,
        performance: result.performance,
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
  const reloadLogs = useCallback(async () => {
    setLogState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchModelGatewayLogs(logQuery);
      setLogState({
        page: result.page,
        pageSize: result.pageSize,
        performance: result.performance,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
    } catch (loadError: unknown) {
      setLogState((current) => ({
        ...current,
        error: normalizeRemoteRowsError(loadError),
        page: current.page,
        pageSize: current.pageSize,
        rows: [],
        status: 'error',
        total: 0,
      }));
    }
  }, [logQuery]);
  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchModelGatewayConfigList(buildModelGatewayListQuery(listQuery))
      .then((result) => {
        if (isCurrent) {
          setListState({
            page: result.page,
            pageSize: result.pageSize,
            performance: result.performance,
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
  useEffect(() => {
    let isCurrent = true;
    setLogState((current) => ({ ...current, status: 'loading' }));
    fetchModelGatewayLogs(logQuery)
      .then((result) => {
        if (isCurrent) {
          setLogState({
            page: result.page,
            pageSize: result.pageSize,
            performance: result.performance,
            rows: result.rows,
            status: 'ready',
            total: result.total,
          });
        }
      })
      .catch((loadError: unknown) => {
        if (isCurrent) {
          setLogState((current) => ({
            ...current,
            error: normalizeRemoteRowsError(loadError),
            page: current.page,
            pageSize: current.pageSize,
            rows: [],
            status: 'error',
            total: 0,
          }));
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [logQuery]);
  const dataSource = listState.rows;

  const openCreateModal = () => {
    setEditingConfig(null);
    setTestResult(null);
    form.resetFields();
    form.setFieldsValue({
      is_default: dataSource.length === 0,
      embedding_connection_mode: 'disabled',
      embedding_dimension: 1536,
      max_retries: 1,
      provider: 'openai_compatible',
      status: 'active',
      test_target: 'chat',
      timeout_seconds: 60,
    });
    setIsModalOpen(true);
  };

  const openEditModal = useCallback((row: ModelGatewayConfigRecord) => {
    setEditingConfig(row);
    setTestResult(null);
    form.setFieldsValue({
      base_url: row.baseUrl,
      default_chat_model: row.defaultChatModel,
      default_embedding_model: row.defaultEmbeddingModel ?? undefined,
      embedding_base_url: row.embeddingBaseUrl ?? undefined,
      embedding_connection_mode: row.embeddingConnectionMode,
      embedding_dimension: row.embeddingDimension ?? 1536,
      is_default: row.isDefault,
      max_retries: row.maxRetries,
      name: row.name,
      provider: row.provider,
      status: row.status,
      test_target: row.embeddingConnectionMode === 'disabled' ? 'chat' : 'chat_and_embedding',
      timeout_seconds: row.timeoutSeconds,
    });
    setIsModalOpen(true);
  }, [form]);

  const buildPayload = (values: ModelGatewayFormValues, options?: { includeTestTarget?: boolean }) => {
    const apiKey = trimText(values.api_key);
    const embeddingApiKey = trimText(values.embedding_api_key);
    const mode = values.embedding_connection_mode ?? 'disabled';
    return {
      base_url: values.base_url.trim(),
      default_chat_model: values.default_chat_model.trim(),
      default_embedding_model: mode === 'disabled' ? null : values.default_embedding_model?.trim(),
      embedding_base_url: mode === 'custom' ? values.embedding_base_url?.trim() : null,
      embedding_connection_mode: mode,
      embedding_dimension: mode === 'disabled' ? null : Number(values.embedding_dimension ?? 1536),
      ...(editingConfig ? { config_id: editingConfig.id } : {}),
      is_default: values.is_default,
      max_retries: Number(values.max_retries ?? 1),
      name: values.name.trim(),
      provider: values.provider.trim(),
      status: values.status,
      ...(options?.includeTestTarget ? { test_target: values.test_target } : {}),
      timeout_seconds: Number(values.timeout_seconds ?? 60),
      ...(apiKey ? { api_key: apiKey } : {}),
      ...(embeddingApiKey ? { embedding_api_key: embeddingApiKey } : {}),
    };
  };

  const handleTest = async () => {
    const testTarget = (form.getFieldValue('test_target') ??
      'chat_and_embedding') as ModelGatewayFormValues['test_target'];
    const effectiveTestTarget = embeddingMode === 'disabled' ? 'chat' : testTarget;
    const fieldsToValidate = [...TEST_TARGET_FIELDS[effectiveTestTarget], 'embedding_connection_mode'];
    if (effectiveTestTarget !== 'chat') {
      fieldsToValidate.push('embedding_dimension');
      if (embeddingMode === 'custom') {
        fieldsToValidate.push('embedding_base_url');
        if (!editingConfig?.embeddingApiKeyConfigured) {
          fieldsToValidate.push('embedding_api_key');
        }
      }
    }
    await form.validateFields(fieldsToValidate);
    const values = form.getFieldsValue();
    setIsTesting(true);
    setTestResult(null);
    try {
      const result = await testModelGatewayConfig({
        ...buildPayload({ ...values, test_target: effectiveTestTarget }, { includeTestTarget: true }),
        test_target: effectiveTestTarget,
      });
      setTestResult(result);
      message[result.ok ? 'success' : 'warning'](result.ok ? '模型网关测试通过' : '模型网关测试未通过');
    } catch (testError) {
      message.error(formatMutationError(testError));
    } finally {
      setIsTesting(false);
    }
  };

  const buildRowTestPayload = useCallback((row: ModelGatewayConfigRecord) => {
    const testTarget: ModelGatewayFormValues['test_target'] =
      row.embeddingConnectionMode === 'disabled' ? 'chat' : 'chat_and_embedding';
    return {
      base_url: row.baseUrl,
      config_id: row.id,
      default_chat_model: row.defaultChatModel,
      default_embedding_model: row.defaultEmbeddingModel ?? undefined,
      embedding_base_url: row.embeddingBaseUrl ?? undefined,
      embedding_connection_mode: row.embeddingConnectionMode,
      embedding_dimension: row.embeddingDimension ?? undefined,
      is_default: row.isDefault,
      max_retries: row.maxRetries,
      name: row.name,
      provider: row.provider,
      status: row.status,
      test_target: testTarget,
      timeout_seconds: row.timeoutSeconds,
    };
  }, []);

  const handleTestConfig = useCallback(async (row: ModelGatewayConfigRecord) => {
    setTestingConfigId(row.id);
    try {
      const result = await testModelGatewayConfig(buildRowTestPayload(row));
      const chatStatus = formatTestStatus(result.chat);
      const embeddingStatus = formatTestStatus(result.embedding);
      message[result.ok ? 'success' : 'warning'](
        `模型网关测试${result.ok ? '通过' : '未通过'}：Chat ${chatStatus}，Embedding ${embeddingStatus}`,
      );
      void reloadLogs();
    } catch (testError) {
      message.error(formatMutationError(testError));
    } finally {
      setTestingConfigId(null);
    }
  }, [buildRowTestPayload, reloadLogs]);

  const handleSave = async () => {
    const values = await form.validateFields();
    const payload = buildPayload(values);
    delete payload.config_id;

    setIsSaving(true);
    try {
      if (editingConfig) {
        await updateModelGatewayConfig(editingConfig.id, payload);
        message.success('模型网关配置已更新');
      } else {
        await createModelGatewayConfig(payload);
        message.success('模型网关配置已创建');
      }
      setIsModalOpen(false);
      void reload();
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = useCallback(async (row: ModelGatewayConfigRecord) => {
    try {
      await deleteModelGatewayConfig(row.id);
      message.success('模型网关配置已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reload]);

  const columns = useMemo<ProColumns<ModelGatewayConfigRecord>[]>(
    () => [
      {
        dataIndex: 'name',
        title: '配置名称',
      },
      {
        dataIndex: 'provider',
        title: 'Provider',
      },
      {
        dataIndex: 'baseUrl',
        title: 'Base URL',
      },
      {
        dataIndex: 'defaultChatModel',
        title: 'Chat 模型',
      },
      {
        dataIndex: 'defaultEmbeddingModel',
        title: 'Embedding 模型',
        render: (_, row) => row.defaultEmbeddingModel || '-',
      },
      {
        dataIndex: 'embeddingConnectionMode',
        title: 'Embedding 连接',
        render: (_, row) => embeddingModeLabels[row.embeddingConnectionMode],
      },
      {
        dataIndex: 'keyStatus',
        title: 'API Key',
        render: (_, row) => (
          <StatusTag color={row.apiKeyConfigured ? 'green' : 'default'} label={row.keyStatus} />
        ),
      },
      {
        dataIndex: 'isDefault',
        title: '默认',
        render: (_, row) =>
          row.isDefault ? <StatusTag color="blue" label="默认" /> : <StatusTag color="default" label="否" />,
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) =>
          row.status === 'active' ? (
            <StatusTag color="green" label="启用" />
          ) : (
            <StatusTag color="default" label="停用" />
          ),
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button
              icon={<ExperimentOutlined />}
              loading={testingConfigId === row.id}
              onClick={() => void handleTestConfig(row)}
              type="link"
            >
              测试
            </Button>
            <Button icon={<EditOutlined />} onClick={() => openEditModal(row)} type="link">
              编辑
            </Button>
            <Popconfirm
              okText="删除"
              onConfirm={() => handleDelete(row)}
              title={`删除模型网关配置 ${row.name}？`}
            >
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDelete, handleTestConfig, openEditModal, testingConfigId],
  );
  const logColumns = useMemo<ColumnsType<ModelGatewayLogRecord>>(
    () => [
      {
        dataIndex: 'id',
        fixed: 'left',
        key: 'id',
        sorter: true,
        title: '日志 ID',
        width: 220,
        render: (_, row) => (
          <Space orientation="vertical" size={2}>
            <Typography.Text copyable ellipsis style={{ maxWidth: 200 }}>
              {row.id}
            </Typography.Text>
            <ExecutionTraceLink sourceId={row.id} sourceType="model_gateway_log">
              调用诊断
            </ExecutionTraceLink>
          </Space>
        ),
      },
      {
        dataIndex: 'purpose',
        key: 'purpose',
        sorter: true,
        title: '用途',
        width: 150,
      },
      {
        dataIndex: 'model',
        key: 'model',
        sorter: true,
        title: '模型',
        width: 170,
      },
      {
        dataIndex: 'status',
        key: 'status',
        sorter: true,
        title: '状态',
        width: 110,
        render: (_, row) => (
          <StatusTag
            color={row.status === 'succeeded' ? 'green' : row.status === 'failed' ? 'red' : 'default'}
            label={row.status}
          />
        ),
      },
      {
        dataIndex: 'latencyMs',
        key: 'latencyMs',
        sorter: true,
        title: '耗时',
        width: 100,
        render: (_, row) => (typeof row.latencyMs === 'number' ? `${row.latencyMs}ms` : '-'),
      },
      {
        dataIndex: 'tokens',
        ellipsis: true,
        title: 'Token',
        width: 240,
        render: (_, row) => formatTokenSummary(row.tokens),
      },
      {
        dataIndex: 'aiTaskId',
        key: 'aiTaskId',
        sorter: true,
        title: 'AI 任务',
        width: 180,
        render: (_, row) => row.aiTaskId || '-',
      },
      {
        dataIndex: 'error',
        ellipsis: true,
        title: '错误',
        width: 220,
        render: (_, row) => row.error || '-',
      },
      {
        dataIndex: 'createdAt',
        defaultSortOrder: 'descend',
        key: 'createdAt',
        sorter: true,
        title: '创建时间',
        width: 180,
        render: (_, row) => formatDisplayDateTime(row.createdAt),
      },
    ],
    [],
  );

  const modelGatewayLogPanel = (
    <div style={{ marginBottom: 16 }}>
      <Space align="center" style={{ justifyContent: 'space-between', marginBottom: 12, width: '100%' }}>
        <Space align="baseline" size={12}>
          <Typography.Title level={5} style={{ margin: 0 }}>
            最近模型调用日志
          </Typography.Title>
          <Typography.Text type="secondary">共 {logState.total} 条</Typography.Text>
          {logState.performance?.duration_ms !== undefined ? (
            <Tag color={logState.performance.slow ? 'orange' : 'default'}>
              查询 {formatDuration(logState.performance.duration_ms)}
            </Tag>
          ) : null}
        </Space>
        <Button onClick={() => void reloadLogs()}>刷新日志</Button>
      </Space>
      {logState.error ? (
        <Alert
          showIcon
          style={{ marginBottom: 12 }}
          title={formatRemoteRowsError(logState.error)}
          type="warning"
        />
      ) : null}
      <Table<ModelGatewayLogRecord>
        columns={logColumns}
        dataSource={logState.rows}
        loading={logState.status === 'loading'}
        onChange={(pagination, _filters, sorter) => {
          const nextSorter = resolveModelGatewayLogSorter(sorter);
          setLogQuery((current) => ({
            ...current,
            page: pagination.current ?? 1,
            pageSize: pagination.pageSize ?? current.pageSize,
            sortField: nextSorter.sortField,
            sortOrder: nextSorter.sortOrder,
          }));
        }}
        pagination={{
          current: logState.page,
          pageSize: logState.pageSize,
          showSizeChanger: false,
          showTotal: (total) => `共 ${total} 条`,
          total: logState.total,
        }}
        rowKey="id"
        scroll={{ x: 1400 }}
        tableLayout="fixed"
      />
    </div>
  );

  return (
    <>
      <ManagementListPage<ModelGatewayConfigRecord>
        breadcrumbGroup="系统管理"
        columns={columns}
        dataSource={dataSource}
        viewStorageKey="system.model_gateway"
        filters={[
          { label: '配置名称', name: 'name', type: 'text' },
          { label: 'Provider', name: 'provider', type: 'text' },
          { label: 'Chat 模型', name: 'defaultChatModel', type: 'text' },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '启用', value: 'active' },
              { label: '停用', value: 'inactive' },
            ],
            type: 'select',
          },
          {
            label: 'Embedding 连接',
            name: 'embeddingConnectionMode',
            options: [
              { label: '禁用', value: 'disabled' },
              { label: '复用 Chat', value: 'reuse_chat' },
              { label: '单独配置', value: 'custom' },
            ],
            type: 'select',
          },
          {
            label: '默认',
            name: 'isDefault',
            options: [
              { label: '默认', value: 'true' },
              { label: '否', value: 'false' },
            ],
            type: 'select',
          },
        ]}
        loading={listState.status === 'loading'}
        notice={formatRemoteRowsError(listState.error)}
        beforeTable={modelGatewayLogPanel}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="新增配置"
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        tableLayout="fixed"
        tableTitle="模型网关配置"
        title="模型网关"
      />
      <Modal
        cancelText="取消"
        confirmLoading={isSaving}
        destroyOnHidden
        okText="保存"
        onCancel={() => setIsModalOpen(false)}
        onOk={() => void handleSave()}
        open={isModalOpen}
        title={editingConfig ? '编辑模型网关配置' : '新增模型网关配置'}
      >
        <Form<ModelGatewayFormValues> form={form} layout="vertical">
          <Form.Item label="配置名称" name="name" rules={[{ required: true, message: '请输入配置名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Provider" name="provider" rules={[{ required: true, message: '请输入 Provider' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Base URL" name="base_url" rules={[{ required: true, message: '请输入 Base URL' }]}>
            <Input placeholder="https://api.example.com/v1" />
          </Form.Item>
          <Form.Item
            extra={editingConfig ? '留空表示保留当前服务端密钥。' : undefined}
            label="API Key"
            name="api_key"
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item
            label="默认 Chat 模型"
            name="default_chat_model"
            rules={[{ required: true, message: '请输入默认 Chat 模型' }]}
          >
            <AutoComplete options={chatModelOptions} />
          </Form.Item>
          <Divider>Embedding 网关</Divider>
          <Form.Item
            label="连接模式"
            name="embedding_connection_mode"
            rules={[{ required: true, message: '请选择 Embedding 连接模式' }]}
          >
            <Radio.Group
              options={[
                { label: '禁用', value: 'disabled' },
                { label: '复用 Chat', value: 'reuse_chat' },
                { label: '单独配置', value: 'custom' },
              ]}
              onChange={(event) => {
                if (event.target.value === 'disabled') {
                  form.setFieldsValue({ test_target: 'chat' });
                }
              }}
            />
          </Form.Item>
          {embeddingMode !== 'disabled' ? (
            <>
              <Form.Item
                label="默认 Embedding 模型"
                name="default_embedding_model"
                rules={[{ required: true, message: '请输入默认 Embedding 模型' }]}
              >
                <AutoComplete options={embeddingModelOptions} />
              </Form.Item>
              <Form.Item
                label="Embedding 维度"
                name="embedding_dimension"
                rules={[{ required: true, message: '请输入 Embedding 维度' }]}
              >
                <InputNumber min={1} precision={0} style={{ width: '100%' }} />
              </Form.Item>
            </>
          ) : null}
          {embeddingMode === 'custom' ? (
            <>
              <Form.Item
                label="Embedding Base URL"
                name="embedding_base_url"
                rules={[{ required: true, message: '请输入 Embedding Base URL' }]}
              >
                <Input placeholder="https://embedding.example.com/v1" />
              </Form.Item>
              <Form.Item
                extra={editingConfig?.embeddingApiKeyConfigured ? '留空表示保留当前 Embedding 密钥。' : undefined}
                label="Embedding API Key"
                name="embedding_api_key"
                rules={[
                  {
                    required: !editingConfig?.embeddingApiKeyConfigured,
                    message: '请输入 Embedding API Key',
                  },
                ]}
              >
                <Input.Password autoComplete="new-password" />
              </Form.Item>
            </>
          ) : null}
          <Form.Item label="超时秒数" name="timeout_seconds" rules={[{ required: true, message: '请输入超时秒数' }]}>
            <InputNumber min={1} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="最大重试" name="max_retries" rules={[{ required: true, message: '请输入最大重试次数' }]}>
            <InputNumber min={0} precision={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
            <Select
              options={[
                { label: '启用', value: 'active' },
                { label: '停用', value: 'inactive' },
              ]}
            />
          </Form.Item>
          <Form.Item label="默认配置" name="is_default" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item>
            <Space orientation="vertical" size={8} style={{ width: '100%' }}>
              <Form.Item label="测试范围" name="test_target" style={{ marginBottom: 0 }}>
                <Radio.Group
                  options={[
                    { label: 'Chat + Embedding', value: 'chat_and_embedding' },
                    { label: '仅 Chat', value: 'chat' },
                    { label: '仅 Embedding', value: 'embedding', disabled: embeddingMode === 'disabled' },
                  ]}
                />
              </Form.Item>
              <Button loading={isTesting} onClick={() => void handleTest()}>
                测试连接
              </Button>
              {testResult ? (
                <Alert
                  title={`Chat ${formatTestStatus(testResult.chat)} / Embedding ${formatTestStatus(
                    testResult.embedding,
                  )}`}
                  description={`Chat: ${testResult.chat.model}，${testResult.chat.latency_ms ?? 0}ms；Embedding: ${
                    testResult.embedding.model
                  }${
                    testResult.embedding.status === 'skipped' ? '' : `，${testResult.embedding.latency_ms ?? 0}ms`
                  }${
                    testResult.embedding.dimension ? `，维度 ${testResult.embedding.dimension}` : ''
                  }`}
                  showIcon
                  type={testResult.ok ? 'success' : 'warning'}
                />
              ) : null}
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
