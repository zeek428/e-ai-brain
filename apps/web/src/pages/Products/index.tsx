import { DeleteOutlined, EditOutlined, PlusOutlined, SettingOutlined } from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import type {
  ProductGitRepositoryRecord,
  ProductModuleRecord,
  ProductRecord,
  ProductRelatedSystemRecord,
  ProductVersionRecord,
} from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createManagementProduct,
  createProductGitRepository,
  createProductModule,
  createProductRelatedSystem,
  createProductVersion,
  deleteManagementProduct,
  deleteProductGitRepository,
  deleteProductModule,
  deleteProductRelatedSystem,
  deleteProductVersion,
  fetchManagementProducts,
  fetchProductGitRepositoryRecords,
  fetchProductModules,
  fetchProductRelatedSystems,
  fetchProductVersions,
  updateManagementProduct,
  updateProductGitRepository,
  updateProductModule,
  updateProductRelatedSystem,
  updateProductVersion,
  type ProductGitRepositoryMutationPayload,
  type ProductModuleMutationPayload,
  type ProductRelatedSystemMutationPayload,
  type ProductVersionMutationPayload,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';

type ProductFormValues = {
  code?: string;
  default_version_code?: string;
  default_version_name?: string;
  description?: string;
  name: string;
  owner_team?: string;
  status: ProductRecord['status'];
};

type ResourceKind = 'module' | 'relatedSystem' | 'repository' | 'version';

type ProductResourceFormValues = {
  code?: string;
  credential_ref?: string;
  default_branch?: string;
  description?: string;
  name: string;
  owner_team?: string;
  project_id?: string;
  project_path?: string;
  release_date?: string;
  remote_url?: string;
  repo_type?: string;
  root_path?: string;
  start_date?: string;
  status?: string;
};

type ProductResourceEditor =
  | { kind: 'module'; record?: ProductModuleRecord; submitting: boolean }
  | { kind: 'relatedSystem'; record?: ProductRelatedSystemRecord; submitting: boolean }
  | { kind: 'repository'; record?: ProductGitRepositoryRecord; submitting: boolean }
  | { kind: 'version'; record?: ProductVersionRecord; submitting: boolean };

const versionStatusLabels: Record<ProductVersionRecord['status'], { color: string; label: string }> = {
  active: { color: 'green', label: '启用' },
  archived: { color: 'default', label: '归档' },
  planning: { color: 'gold', label: '规划中' },
};

const activeStatusLabels: Record<'active' | 'inactive', { color: string; label: string }> = {
  active: { color: 'green', label: '启用' },
  inactive: { color: 'default', label: '停用' },
};

function resourceEditorTitle(editor?: ProductResourceEditor) {
  if (!editor) {
    return '产品配置';
  }
  const action = editor.record ? '编辑' : '新增';
  if (editor.kind === 'version') {
    return `${action}版本`;
  }
  if (editor.kind === 'module') {
    return `${action}模块`;
  }
  if (editor.kind === 'relatedSystem') {
    return `${action}相关系统`;
  }
  return `${action} Git 资源`;
}

export default function ProductsPage() {
  const [form] = Form.useForm<ProductFormValues>();
  const [resourceForm] = Form.useForm<ProductResourceFormValues>();
  const [editingProduct, setEditingProduct] = useState<ProductRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [configProduct, setConfigProduct] = useState<ProductRecord | null>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [versionRows, setVersionRows] = useState<ProductVersionRecord[]>([]);
  const [moduleRows, setModuleRows] = useState<ProductModuleRecord[]>([]);
  const [relatedSystemRows, setRelatedSystemRows] = useState<ProductRelatedSystemRecord[]>([]);
  const [repositoryRows, setRepositoryRows] = useState<ProductGitRepositoryRecord[]>([]);
  const [resourceEditor, setResourceEditor] = useState<ProductResourceEditor>();
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchManagementProducts);

  const loadProductResources = useCallback(async (productId: string) => {
    setConfigLoading(true);
    try {
      const [versions, modules, relatedSystems, repositories] = await Promise.all([
        fetchProductVersions(productId),
        fetchProductModules(productId),
        fetchProductRelatedSystems(productId),
        fetchProductGitRepositoryRecords(productId),
      ]);
      setVersionRows(versions);
      setModuleRows(modules);
      setRelatedSystemRows(relatedSystems);
      setRepositoryRows(repositories);
    } catch (loadError) {
      message.error(formatMutationError(loadError));
    } finally {
      setConfigLoading(false);
    }
  }, []);

  const openCreateModal = () => {
    setEditingProduct(null);
    form.resetFields();
    form.setFieldsValue({
      default_version_code: 'v1',
      default_version_name: 'v1',
      status: 'active',
    });
    setIsModalOpen(true);
  };

  const openEditModal = useCallback((row: ProductRecord) => {
    setEditingProduct(row);
    form.setFieldsValue({
      code: row.code,
      name: row.name,
      owner_team: row.ownerTeam === '-' ? undefined : row.ownerTeam,
      status: row.status,
    });
    setIsModalOpen(true);
  }, [form]);

  const openConfigModal = useCallback((row: ProductRecord) => {
    setConfigProduct(row);
    void loadProductResources(row.id);
  }, [loadProductResources]);

  const closeConfigModal = useCallback(() => {
    setConfigProduct(null);
    setVersionRows([]);
    setModuleRows([]);
    setRelatedSystemRows([]);
    setRepositoryRows([]);
  }, []);

  const handleSave = async () => {
    const values = await form.validateFields();
    const payload = {
      code: trimText(values.code),
      description: trimText(values.description),
      name: values.name.trim(),
      owner_team: trimText(values.owner_team),
      status: values.status,
    };

    setIsSaving(true);
    try {
      if (editingProduct) {
        await updateManagementProduct(editingProduct.id, payload);
        message.success('产品已更新');
      } else {
        const createdProduct = await createManagementProduct(payload);
        const defaultVersionName = trimText(values.default_version_name);
        if (defaultVersionName) {
          await createProductVersion(createdProduct.id, {
            code: trimText(values.default_version_code) ?? defaultVersionName,
            name: defaultVersionName,
            status: 'active',
          });
        }
        message.success('产品已创建');
      }
      setIsModalOpen(false);
      void reload();
    } catch (saveError) {
      message.error(formatMutationError(saveError));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = useCallback(async (row: ProductRecord) => {
    try {
      await deleteManagementProduct(row.id);
      message.success('产品已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reload]);

  const openResourceEditor = useCallback((kind: ResourceKind, record?: ProductResourceEditor['record']) => {
    resourceForm.resetFields();
    if (kind === 'version') {
      const version = record as ProductVersionRecord | undefined;
      resourceForm.setFieldsValue({
        code: version?.code,
        name: version?.name,
        release_date: version?.releaseDate,
        start_date: version?.startDate,
        status: version?.status ?? 'active',
      });
      setResourceEditor({ kind, record: version, submitting: false });
      return;
    }
    if (kind === 'module') {
      const module = record as ProductModuleRecord | undefined;
      resourceForm.setFieldsValue({
        code: module?.code,
        name: module?.name,
        owner_team: module?.ownerTeam === '-' ? undefined : module?.ownerTeam,
        status: module?.status ?? 'active',
      });
      setResourceEditor({ kind, record: module, submitting: false });
      return;
    }
    if (kind === 'relatedSystem') {
      const relatedSystem = record as ProductRelatedSystemRecord | undefined;
      resourceForm.setFieldsValue({
        code: relatedSystem?.code,
        description: relatedSystem?.description ?? undefined,
        name: relatedSystem?.name,
        owner_team: relatedSystem?.ownerTeam === '-' ? undefined : relatedSystem?.ownerTeam,
        status: relatedSystem?.status ?? 'active',
      });
      setResourceEditor({ kind, record: relatedSystem, submitting: false });
      return;
    }
    const repository = record as ProductGitRepositoryRecord | undefined;
    resourceForm.setFieldsValue({
      default_branch: repository?.defaultBranch ?? 'main',
      name: repository?.name,
      project_id: repository?.projectId ?? undefined,
      project_path: repository?.projectPath ?? undefined,
      remote_url: repository?.remoteUrl === '-' ? undefined : repository?.remoteUrl,
      repo_type: repository?.repoType ?? 'code',
      root_path: repository?.rootPath ?? '/',
      status: repository?.status ?? 'active',
    });
    setResourceEditor({ kind, record: repository, submitting: false });
  }, [resourceForm]);

  const reloadConfigAfterMutation = useCallback(async () => {
    if (!configProduct) {
      return;
    }
    await loadProductResources(configProduct.id);
    await reload();
  }, [configProduct, loadProductResources, reload]);

  const handleSaveResource = async () => {
    if (!configProduct || !resourceEditor) {
      return;
    }
    const values = await resourceForm.validateFields();
    setResourceEditor((current) => (current ? { ...current, submitting: true } : current));
    try {
      if (resourceEditor.kind === 'version') {
        const payload: ProductVersionMutationPayload = {
          code: trimText(values.code),
          name: values.name.trim(),
          release_date: trimText(values.release_date),
          start_date: trimText(values.start_date),
          status: values.status ?? 'active',
        };
        if (resourceEditor.record) {
          await updateProductVersion(resourceEditor.record.id, payload);
        } else {
          await createProductVersion(configProduct.id, payload);
        }
      }
      if (resourceEditor.kind === 'module') {
        const payload: ProductModuleMutationPayload = {
          code: trimText(values.code),
          name: values.name.trim(),
          owner_team: trimText(values.owner_team),
          status: values.status ?? 'active',
        };
        if (resourceEditor.record) {
          await updateProductModule(resourceEditor.record.id, payload);
        } else {
          await createProductModule(configProduct.id, payload);
        }
      }
      if (resourceEditor.kind === 'repository') {
        const payload: ProductGitRepositoryMutationPayload = {
          credential_ref: trimText(values.credential_ref),
          default_branch: trimText(values.default_branch) ?? 'main',
          git_provider: 'gitlab',
          name: values.name.trim(),
          project_id: trimText(values.project_id),
          project_path: trimText(values.project_path),
          remote_url: trimText(values.remote_url),
          repo_type: trimText(values.repo_type) ?? 'code',
          root_path: trimText(values.root_path) ?? '/',
          status: values.status ?? 'active',
        };
        if (resourceEditor.record) {
          if (!payload.credential_ref) {
            delete payload.credential_ref;
          }
          await updateProductGitRepository(resourceEditor.record.id, payload);
        } else {
          await createProductGitRepository(configProduct.id, payload);
        }
      }
      if (resourceEditor.kind === 'relatedSystem') {
        const payload: ProductRelatedSystemMutationPayload = {
          code: trimText(values.code),
          description: trimText(values.description),
          name: values.name.trim(),
          owner_team: trimText(values.owner_team),
          status: values.status ?? 'active',
        };
        if (resourceEditor.record) {
          await updateProductRelatedSystem(resourceEditor.record.id, payload);
        } else {
          await createProductRelatedSystem(configProduct.id, payload);
        }
      }
      message.success('产品配置已保存');
      setResourceEditor(undefined);
      await reloadConfigAfterMutation();
    } catch (saveError) {
      setResourceEditor((current) => (current ? { ...current, submitting: false } : current));
      message.error(formatMutationError(saveError));
    }
  };

  const handleDeleteResource = useCallback(async (kind: ResourceKind, id: string) => {
    try {
      if (kind === 'version') {
        await deleteProductVersion(id);
      }
      if (kind === 'module') {
        await deleteProductModule(id);
      }
      if (kind === 'repository') {
        await deleteProductGitRepository(id);
      }
      if (kind === 'relatedSystem') {
        await deleteProductRelatedSystem(id);
      }
      message.success('产品配置已删除');
      await reloadConfigAfterMutation();
    } catch (deleteError) {
      message.error(formatMutationError(deleteError));
    }
  }, [reloadConfigAfterMutation]);

  const versionColumns = useMemo<ProColumns<ProductVersionRecord>[]>(
    () => [
      { dataIndex: 'code', search: false, title: '版本编码' },
      { dataIndex: 'name', search: false, title: '版本名称' },
      {
        dataIndex: 'status',
        search: false,
        title: '状态',
        render: (_, row) => {
          const statusLabel = versionStatusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
      },
      {
        key: 'actions',
        search: false,
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button icon={<EditOutlined />} onClick={() => openResourceEditor('version', row)} type="link">
              编辑
            </Button>
            <Popconfirm okText="删除" onConfirm={() => handleDeleteResource('version', row.id)} title={`删除版本 ${row.code}？`}>
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDeleteResource, openResourceEditor],
  );

  const moduleColumns = useMemo<ProColumns<ProductModuleRecord>[]>(
    () => [
      { dataIndex: 'code', search: false, title: '模块编码' },
      { dataIndex: 'name', search: false, title: '模块名称' },
      { dataIndex: 'ownerTeam', search: false, title: '负责团队' },
      {
        dataIndex: 'status',
        search: false,
        title: '状态',
        render: (_, row) => {
          const statusLabel = activeStatusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
      },
      {
        key: 'actions',
        search: false,
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button icon={<EditOutlined />} onClick={() => openResourceEditor('module', row)} type="link">
              编辑
            </Button>
            <Popconfirm okText="删除" onConfirm={() => handleDeleteResource('module', row.id)} title={`删除模块 ${row.code}？`}>
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDeleteResource, openResourceEditor],
  );

  const repositoryColumns = useMemo<ProColumns<ProductGitRepositoryRecord>[]>(
    () => [
      { dataIndex: 'name', search: false, title: '资源名称' },
      { dataIndex: 'provider', search: false, title: 'Provider' },
      { dataIndex: 'projectPath', search: false, title: 'Project Path' },
      { dataIndex: 'remoteUrl', search: false, title: 'Remote URL' },
      { dataIndex: 'credentialStatus', search: false, title: '凭据状态' },
      {
        dataIndex: 'status',
        search: false,
        title: '状态',
        render: (_, row) => {
          const statusLabel = activeStatusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
      },
      {
        key: 'actions',
        search: false,
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button icon={<EditOutlined />} onClick={() => openResourceEditor('repository', row)} type="link">
              编辑
            </Button>
            <Popconfirm okText="删除" onConfirm={() => handleDeleteResource('repository', row.id)} title={`删除 Git 资源 ${row.name}？`}>
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDeleteResource, openResourceEditor],
  );

  const relatedSystemColumns = useMemo<ProColumns<ProductRelatedSystemRecord>[]>(
    () => [
      { dataIndex: 'code', search: false, title: '系统编码' },
      { dataIndex: 'name', search: false, title: '系统名称' },
      { dataIndex: 'ownerTeam', search: false, title: '负责团队' },
      {
        dataIndex: 'status',
        search: false,
        title: '状态',
        render: (_, row) => {
          const statusLabel = activeStatusLabels[row.status];
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
      },
      {
        key: 'actions',
        search: false,
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button
              icon={<EditOutlined />}
              onClick={() => openResourceEditor('relatedSystem', row)}
              type="link"
            >
              编辑
            </Button>
            <Popconfirm
              okText="删除"
              onConfirm={() => handleDeleteResource('relatedSystem', row.id)}
              title={`删除相关系统 ${row.code}？`}
            >
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDeleteResource, openResourceEditor],
  );

  const columns = useMemo<ProColumns<ProductRecord>[]>(
    () => [
      {
        dataIndex: 'code',
        title: '产品编码',
      },
      {
        dataIndex: 'name',
        title: '产品名称',
      },
      {
        dataIndex: 'ownerTeam',
        title: '负责团队',
      },
      {
        dataIndex: 'version',
        title: '当前版本',
      },
      {
        dataIndex: 'moduleCount',
        title: '模块数',
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
              aria-label="配置"
              icon={<SettingOutlined />}
              onClick={() => openConfigModal(row)}
              type="link"
            >
              配置
            </Button>
            <Button icon={<EditOutlined />} onClick={() => openEditModal(row)} type="link">
              编辑
            </Button>
            <Popconfirm
              okText="删除"
              onConfirm={() => handleDelete(row)}
              title={`删除产品 ${row.code}？`}
            >
              <Button danger icon={<DeleteOutlined />} type="link">
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
      },
    ],
    [handleDelete, openConfigModal, openEditModal],
  );

  return (
    <>
      <ManagementListPage<ProductRecord>
        breadcrumbGroup="产品资产"
        columns={columns}
        dataSource={dataSource}
        filters={[
          { label: '产品编码', name: 'code', type: 'text' },
          { label: '产品名称', name: 'name', type: 'text' },
          { label: '负责团队', name: 'ownerTeam', type: 'text' },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '启用', value: 'active' },
              { label: '停用', value: 'inactive' },
            ],
            type: 'select',
          },
        ]}
        loading={status === 'loading'}
        notice={formatRemoteRowsError(error)}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="新增产品"
        rowKey="id"
        tableTitle="产品列表"
        title="产品管理"
      />
      <Modal
        confirmLoading={isSaving}
        destroyOnHidden
        onCancel={() => setIsModalOpen(false)}
        onOk={() => void handleSave()}
        open={isModalOpen}
        title={editingProduct ? '编辑产品' : '新增产品'}
      >
        <Form<ProductFormValues> form={form} layout="vertical">
          <Form.Item label="产品编码" name="code" rules={[{ required: true, message: '请输入产品编码' }]}>
            <Input placeholder="请输入唯一产品编码" />
          </Form.Item>
          <Form.Item label="产品名称" name="name" rules={[{ required: true, message: '请输入产品名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="负责团队" name="owner_team">
            <Input />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea autoSize={{ minRows: 3 }} />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
            <Select
              options={[
                { label: '启用', value: 'active' },
                { label: '停用', value: 'inactive' },
              ]}
            />
          </Form.Item>
          {!editingProduct ? (
            <>
              <Form.Item label="默认版本编码" name="default_version_code">
                <Input placeholder="例如 v1" />
              </Form.Item>
              <Form.Item label="默认版本名称" name="default_version_name">
                <Input placeholder="例如 v1" />
              </Form.Item>
            </>
          ) : null}
        </Form>
      </Modal>
      <Modal
        destroyOnHidden
        footer={null}
        onCancel={closeConfigModal}
        open={Boolean(configProduct)}
        title={configProduct ? `产品配置：${configProduct.name}` : '产品配置'}
        width={1080}
      >
        <Space orientation="vertical" size={20} style={{ width: '100%' }}>
          <ProTable<ProductVersionRecord>
            columns={versionColumns}
            dataSource={versionRows}
            headerTitle="版本管理"
            loading={configLoading}
            options={false}
            pagination={false}
            rowKey="id"
            search={false}
            toolBarRender={() => [
              <Button
                aria-label="新增版本"
                icon={<PlusOutlined />}
                key="add-version"
                onClick={() => openResourceEditor('version')}
              >
                新增版本
              </Button>,
            ]}
          />
          <ProTable<ProductModuleRecord>
            columns={moduleColumns}
            dataSource={moduleRows}
            headerTitle="模块管理"
            loading={configLoading}
            options={false}
            pagination={false}
            rowKey="id"
            search={false}
            toolBarRender={() => [
              <Button
                aria-label="新增模块"
                icon={<PlusOutlined />}
                key="add-module"
                onClick={() => openResourceEditor('module')}
              >
                新增模块
              </Button>,
            ]}
          />
          <ProTable<ProductGitRepositoryRecord>
            columns={repositoryColumns}
            dataSource={repositoryRows}
            headerTitle="Git 资源"
            loading={configLoading}
            options={false}
            pagination={false}
            rowKey="id"
            search={false}
            toolBarRender={() => [
              <Button
                aria-label="新增 Git 资源"
                icon={<PlusOutlined />}
                key="add-repository"
                onClick={() => openResourceEditor('repository')}
              >
                新增 Git 资源
              </Button>,
            ]}
          />
          <ProTable<ProductRelatedSystemRecord>
            columns={relatedSystemColumns}
            dataSource={relatedSystemRows}
            headerTitle="相关系统"
            loading={configLoading}
            options={false}
            pagination={false}
            rowKey="id"
            search={false}
            toolBarRender={() => [
              <Button
                aria-label="新增相关系统"
                icon={<PlusOutlined />}
                key="add-related-system"
                onClick={() => openResourceEditor('relatedSystem')}
              >
                新增相关系统
              </Button>,
            ]}
          />
        </Space>
      </Modal>
      <Modal
        cancelText="取消"
        confirmLoading={resourceEditor?.submitting}
        destroyOnHidden
        okButtonProps={{ 'aria-label': '保存' }}
        okText="保存"
        onCancel={() => setResourceEditor(undefined)}
        onOk={() => void handleSaveResource()}
        open={Boolean(resourceEditor)}
        title={resourceEditorTitle(resourceEditor)}
      >
        <Form<ProductResourceFormValues> form={resourceForm} layout="vertical">
          {resourceEditor?.kind === 'version' ? (
            <>
              <Form.Item label="版本编码" name="code" rules={[{ required: true, message: '请输入版本编码' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="版本名称" name="name" rules={[{ required: true, message: '请输入版本名称' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
                <Select
                  options={[
                    { label: '启用', value: 'active' },
                    { label: '规划中', value: 'planning' },
                    { label: '归档', value: 'archived' },
                  ]}
                />
              </Form.Item>
            </>
          ) : null}
          {resourceEditor?.kind === 'module' ? (
            <>
              <Form.Item label="模块编码" name="code" rules={[{ required: true, message: '请输入模块编码' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="模块名称" name="name" rules={[{ required: true, message: '请输入模块名称' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="负责团队" name="owner_team">
                <Input aria-label="模块负责团队" />
              </Form.Item>
              <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
                <Select
                  options={[
                    { label: '启用', value: 'active' },
                    { label: '停用', value: 'inactive' },
                  ]}
                />
              </Form.Item>
            </>
          ) : null}
          {resourceEditor?.kind === 'repository' ? (
            <>
              <Form.Item label="资源名称" name="name" rules={[{ required: true, message: '请输入资源名称' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="Remote URL" name="remote_url">
                <Input />
              </Form.Item>
              <Form.Item label="Project Path" name="project_path" rules={[{ required: true, message: '请输入 Project Path' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="Project ID" name="project_id">
                <Input />
              </Form.Item>
              <Form.Item
                extra={resourceEditor.record ? '留空表示保留服务端已有凭据引用。' : undefined}
                label="凭据引用"
                name="credential_ref"
              >
                <Input />
              </Form.Item>
              <Form.Item label="默认分支" name="default_branch">
                <Input />
              </Form.Item>
              <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
                <Select
                  options={[
                    { label: '启用', value: 'active' },
                    { label: '停用', value: 'inactive' },
                  ]}
                />
              </Form.Item>
            </>
          ) : null}
          {resourceEditor?.kind === 'relatedSystem' ? (
            <>
              <Form.Item label="系统编码" name="code" rules={[{ required: true, message: '请输入系统编码' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="系统名称" name="name" rules={[{ required: true, message: '请输入系统名称' }]}>
                <Input />
              </Form.Item>
              <Form.Item label="系统负责团队" name="owner_team">
                <Input />
              </Form.Item>
              <Form.Item label="描述" name="description">
                <Input.TextArea autoSize={{ minRows: 3 }} />
              </Form.Item>
              <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
                <Select
                  options={[
                    { label: '启用', value: 'active' },
                    { label: '停用', value: 'inactive' },
                  ]}
                />
              </Form.Item>
            </>
          ) : null}
        </Form>
      </Modal>
    </>
  );
}
