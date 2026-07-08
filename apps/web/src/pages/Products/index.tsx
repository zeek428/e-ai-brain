import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  RocketOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, Steps, Tag, Typography, message } from 'antd';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { DateStringPicker } from '../../components/DateStringPicker';
import { ManagementListPage, StatusTag, type ManagementListQuery } from '../../components/ManagementListPage';
import type {
  ProductGitRepositoryRecord,
  ProductModuleRecord,
  ProductRecord,
  ProductRelatedSystemRecord,
  ProductVersionRecord,
} from '../../data/management';
import { formatRemoteRowsError, normalizeRemoteRowsError, type RemoteRowsError } from '../../hooks/useRemoteRows';
import {
  AUTH_STATE_EVENT,
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
  fetchManagementProduct,
  fetchManagementProductList,
  fetchProductGitRepositoryRecords,
  fetchProductModules,
  fetchProductRelatedSystems,
  fetchProductVersions,
  getStoredCurrentUser,
  type CurrentUserResponse,
  updateManagementProduct,
  updateProductGitRepository,
  updateProductModule,
  updateProductRelatedSystem,
  updateProductVersion,
  type ProductGitRepositoryMutationPayload,
  type ProductModuleMutationPayload,
  type ProductRelatedSystemMutationPayload,
  type ProductVersionMutationPayload,
  type RemoteListPerformance,
} from '../../services/aiBrain';
import { formatMutationError, trimText } from '../../utils/managementCrud';
import {
  activeStatusLabels,
  buildProductListQuery,
  canManageProductResources,
  formatProductDeleteError,
  resourceEditorTitle,
  versionCreateStatusOptions,
  versionStatusLabels,
  type ProductFormValues,
  type ProductResourceEditor,
  type ProductResourceFormValues,
  type ResourceKind,
} from './productPageHelpers';
import { navigateTo } from '../../utils/navigation';

const { Paragraph, Text } = Typography;

export default function ProductsPage() {
  const [form] = Form.useForm<ProductFormValues>();
  const [resourceForm] = Form.useForm<ProductResourceFormValues>();
  const [editingProduct, setEditingProduct] = useState<ProductRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [configProduct, setConfigProduct] = useState<ProductRecord | null>(null);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);
  const [versionRows, setVersionRows] = useState<ProductVersionRecord[]>([]);
  const [moduleRows, setModuleRows] = useState<ProductModuleRecord[]>([]);
  const [relatedSystemRows, setRelatedSystemRows] = useState<ProductRelatedSystemRecord[]>([]);
  const [repositoryRows, setRepositoryRows] = useState<ProductGitRepositoryRecord[]>([]);
  const [resourceEditor, setResourceEditor] = useState<ProductResourceEditor>();
  const [handledProductConfigDeepLink, setHandledProductConfigDeepLink] = useState<string>();
  const [currentUser, setCurrentUser] = useState<CurrentUserResponse | undefined>(() => getStoredCurrentUser());
  const canManageProducts = useMemo(
    () => canManageProductResources(currentUser),
    [currentUser],
  );
  const productConfigDeepLink = useMemo(() => {
    const params = new URLSearchParams(window.location.search);
    const productId = params.get('product_id')?.trim();
    if (!productId) {
      return undefined;
    }
    const action = params.get('action')?.trim();
    const resource = params.get('resource')?.trim();
    return {
      action,
      key: `${productId}:${resource ?? ''}:${action ?? ''}`,
      productId,
      resource,
    };
  }, []);
  const [listQuery, setListQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'code',
    sortOrder: 'ascend',
  });
  const [listState, setListState] = useState<{
    error?: RemoteRowsError;
    page: number;
    pageSize: number;
    performance?: RemoteListPerformance;
    rows: ProductRecord[];
    status: 'error' | 'loading' | 'ready';
    total: number;
  }>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const reload = useCallback(async () => {
    setListState((current) => ({ ...current, status: 'loading' }));
    try {
      const result = await fetchManagementProductList(buildProductListQuery(listQuery));
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

  useEffect(() => {
    const syncCurrentUser = () => setCurrentUser(getStoredCurrentUser());
    syncCurrentUser();
    globalThis.addEventListener?.(AUTH_STATE_EVENT, syncCurrentUser);
    return () => {
      globalThis.removeEventListener?.(AUTH_STATE_EVENT, syncCurrentUser);
    };
  }, []);

  useEffect(() => {
    let isCurrent = true;
    setListState((current) => ({ ...current, status: 'loading' }));
    fetchManagementProductList(buildProductListQuery(listQuery))
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
    if (!canManageProducts) {
      message.warning('当前账号只有产品只读权限，不能新增产品');
      return;
    }
    setEditingProduct(null);
    form.resetFields();
    form.setFieldsValue({
      default_version_code: 'v1',
      default_version_name: 'v1',
      status: 'active',
    });
    setIsModalOpen(true);
  };

  const openProductOnboarding = () => {
    setIsOnboardingOpen(true);
  };

  const openFirstProductConfig = () => {
    const product = listState.rows[0];
    if (!product) {
      message.info('请先新增一个产品，再继续配置版本、模块和 Git 资源');
      return;
    }
    setIsOnboardingOpen(false);
    openConfigModal(product);
  };

  const openCreateProductFromOnboarding = () => {
    setIsOnboardingOpen(false);
    openCreateModal();
  };

  const openEditModal = useCallback((row: ProductRecord) => {
    if (!canManageProducts) {
      message.warning('当前账号只有产品只读权限，不能编辑产品');
      return;
    }
    setEditingProduct(row);
    form.setFieldsValue({
      code: row.code,
      name: row.name,
      owner_team: row.ownerTeam === '-' ? undefined : row.ownerTeam,
      status: row.status,
    });
    setIsModalOpen(true);
  }, [canManageProducts, form]);

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
    if (!canManageProducts) {
      message.warning('当前账号只有产品只读权限，不能保存产品');
      return;
    }
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
    if (!canManageProducts) {
      message.warning('当前账号只有产品只读权限，不能删除产品');
      return;
    }
    try {
      await deleteManagementProduct(row.id);
      message.success('产品已删除');
      await reload();
    } catch (deleteError) {
      message.error(formatProductDeleteError(deleteError));
    }
  }, [canManageProducts, reload]);

  const openResourceEditor = useCallback((kind: ResourceKind, record?: ProductResourceEditor['record']) => {
    if (!canManageProducts) {
      message.warning('当前账号只有产品只读权限，不能维护产品配置');
      return;
    }
    resourceForm.resetFields();
    if (kind === 'version') {
      const version = record as ProductVersionRecord | undefined;
      resourceForm.setFieldsValue({
        code: version?.code,
        name: version?.name,
        release_date: version?.releaseDate,
        start_date: version?.startDate,
        status: version?.status ?? 'planning',
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
      git_provider: repository?.provider ?? 'gitlab',
      name: repository?.name,
      project_id: repository?.projectId ?? undefined,
      project_path: repository?.projectPath ?? undefined,
      remote_url: repository?.remoteUrl === '-' ? undefined : repository?.remoteUrl,
      repo_type: repository?.repoType ?? 'code',
      root_path: repository?.rootPath ?? '/',
      status: repository?.status ?? 'active',
    });
    setResourceEditor({ kind, record: repository, submitting: false });
  }, [canManageProducts, resourceForm]);

  useEffect(() => {
    if (!productConfigDeepLink || handledProductConfigDeepLink === productConfigDeepLink.key) {
      return undefined;
    }
    let cancelled = false;
    const openDeepLinkedProductConfig = (product: ProductRecord) => {
      if (cancelled) {
        return;
      }
      setHandledProductConfigDeepLink(productConfigDeepLink.key);
      openConfigModal(product);
      if (
        productConfigDeepLink.resource === 'repository'
        && productConfigDeepLink.action === 'create'
      ) {
        queueMicrotask(() => {
          if (!cancelled) {
            openResourceEditor('repository');
          }
        });
      }
    };
    const listedProduct = listState.rows.find(
      (product) => product.id === productConfigDeepLink.productId,
    );
    if (listedProduct) {
      openDeepLinkedProductConfig(listedProduct);
      return () => {
        cancelled = true;
      };
    }
    void fetchManagementProduct(productConfigDeepLink.productId)
      .then(openDeepLinkedProductConfig)
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setHandledProductConfigDeepLink(productConfigDeepLink.key);
        message.error(formatMutationError(error));
      });
    return () => {
      cancelled = true;
    };
  }, [
    handledProductConfigDeepLink,
    listState.rows,
    openConfigModal,
    openResourceEditor,
    productConfigDeepLink,
  ]);

  const reloadConfigAfterMutation = useCallback(async () => {
    if (!configProduct) {
      return;
    }
    await loadProductResources(configProduct.id);
    await reload();
  }, [configProduct, loadProductResources, reload]);

  const handleSaveResource = async () => {
    if (!canManageProducts) {
      message.warning('当前账号只有产品只读权限，不能保存产品配置');
      return;
    }
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
        };
        if (resourceEditor.record) {
          await updateProductVersion(resourceEditor.record.id, payload);
        } else {
          await createProductVersion(configProduct.id, {
            ...payload,
            status: values.status ?? 'active',
          });
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
        const projectPathValue = trimText(values.project_path);
        const originalProjectPath = resourceEditor.record
          ? trimText(resourceEditor.record.projectPath ?? undefined)
          : undefined;
        const projectPathChanged = projectPathValue !== originalProjectPath;
        const payload: ProductGitRepositoryMutationPayload = {
          credential_ref: trimText(values.credential_ref),
          default_branch: trimText(values.default_branch) ?? 'main',
          git_provider: values.git_provider ?? 'gitlab',
          name: values.name.trim(),
          project_id: trimText(values.project_id),
          project_path: projectPathValue,
          remote_url: trimText(values.remote_url),
          repo_type: trimText(values.repo_type) ?? 'code',
          root_path: trimText(values.root_path) ?? '/',
          status: values.status ?? 'active',
        };
        if (resourceEditor.record) {
          if (!payload.credential_ref) {
            delete payload.credential_ref;
          }
          if (projectPathChanged) {
            payload.project_path = projectPathValue ?? null;
          } else {
            delete payload.project_path;
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
    if (!canManageProducts) {
      message.warning('当前账号只有产品只读权限，不能删除产品配置');
      return;
    }
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
  }, [canManageProducts, reloadConfigAfterMutation]);

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
      ...(canManageProducts
        ? [
            {
              key: 'actions',
              search: false,
              title: '操作',
              valueType: 'option' as const,
              render: (_: unknown, row: ProductVersionRecord) => (
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
          ]
        : []),
    ],
    [canManageProducts, handleDeleteResource, openResourceEditor],
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
      ...(canManageProducts
        ? [
            {
              key: 'actions',
              search: false,
              title: '操作',
              valueType: 'option' as const,
              render: (_: unknown, row: ProductModuleRecord) => (
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
          ]
        : []),
    ],
    [canManageProducts, handleDeleteResource, openResourceEditor],
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
      ...(canManageProducts
        ? [
            {
              key: 'actions',
              search: false,
              title: '操作',
              valueType: 'option' as const,
              render: (_: unknown, row: ProductGitRepositoryRecord) => (
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
          ]
        : []),
    ],
    [canManageProducts, handleDeleteResource, openResourceEditor],
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
      ...(canManageProducts
        ? [
            {
              key: 'actions',
              search: false,
              title: '操作',
              valueType: 'option' as const,
              render: (_: unknown, row: ProductRelatedSystemRecord) => (
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
          ]
        : []),
    ],
    [canManageProducts, handleDeleteResource, openResourceEditor],
  );

  const columns = useMemo<ProColumns<ProductRecord>[]>(
    () => [
      {
        dataIndex: 'code',
        sorter: true,
        title: '产品编码',
      },
      {
        dataIndex: 'name',
        sorter: true,
        title: '产品名称',
      },
      {
        dataIndex: 'ownerTeam',
        sorter: true,
        title: '负责团队',
      },
      {
        dataIndex: 'version',
        sorter: true,
        title: '当前版本',
      },
      {
        dataIndex: 'moduleCount',
        sorter: true,
        title: '模块数',
      },
      {
        dataIndex: 'status',
        sorter: true,
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
            {canManageProducts ? (
              <>
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
              </>
            ) : null}
          </Space>
        ),
      },
    ],
    [canManageProducts, handleDelete, openConfigModal, openEditModal],
  );

  return (
    <>
      <ManagementListPage<ProductRecord>
        breadcrumbGroup="产品资产"
        columns={columns}
        dataSource={listState.rows}
        viewStorageKey="assets.products"
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
        loading={listState.status === 'loading'}
        notice={formatRemoteRowsError(listState.error)}
        onPrimaryAction={canManageProducts ? openCreateModal : undefined}
        onReload={() => void reload()}
        primaryAction={canManageProducts ? '新增产品' : undefined}
        remote={{
          onChange: setListQuery,
          page: listState.page,
          pageSize: listState.pageSize,
          performance: listState.performance,
          total: listState.total,
        }}
        rowKey="id"
        tableTitle="产品列表"
        title="产品管理"
        toolbarActions={[
          <Button
            aria-label="产品接入向导"
            icon={<RocketOutlined />}
            key="product-onboarding"
            onClick={openProductOnboarding}
          >
            产品接入向导
          </Button>,
        ]}
      />
      <Modal
        destroyOnHidden
        footer={[
          <Button key="health" onClick={() => navigateTo('/system/health')}>
            复检系统健康
          </Button>,
          canManageProducts ? (
            <Button key="create" onClick={openCreateProductFromOnboarding} type="primary">
              新增产品
            </Button>
          ) : null,
        ]}
        onCancel={() => setIsOnboardingOpen(false)}
        open={isOnboardingOpen}
        title="产品接入向导"
        width={920}
      >
        <Space className="product-onboarding-guide" orientation="vertical" size={18}>
          <Paragraph>
            按产品维度完成主数据、交付结构、代码资源、知识空间、插件连接和权限范围配置后，
            后续需求、Bug、代码巡检、知识检索和作业运行才能稳定归属到同一个产品上下文。
          </Paragraph>
          <div className="product-onboarding-status">
            <Tag color={listState.total > 0 ? 'green' : 'gold'}>
              已有产品 {listState.total}
            </Tag>
            <Tag color={listState.rows.some((product) => product.moduleCount > 0) ? 'green' : 'default'}>
              当前页已有模块的产品 {listState.rows.filter((product) => product.moduleCount > 0).length}
            </Tag>
            <Tag color={listState.rows.some((product) => product.version && product.version !== '-') ? 'green' : 'default'}>
              当前页已有版本的产品 {listState.rows.filter((product) => product.version && product.version !== '-').length}
            </Tag>
          </div>
          <Steps
            orientation="vertical"
            items={[
              {
                content: (
                  <Space orientation="vertical" size={6}>
                    <Text>创建产品编码、产品名称、负责团队和默认版本。</Text>
                    <Space wrap>
                      {canManageProducts ? (
                        <Button onClick={openCreateProductFromOnboarding} size="small" type="primary">
                          新增产品
                        </Button>
                      ) : null}
                      <Button onClick={() => setIsOnboardingOpen(false)} size="small">
                        查看产品列表
                      </Button>
                    </Space>
                  </Space>
                ),
                title: '1. 建立产品主数据',
              },
              {
                content: (
                  <Space orientation="vertical" size={6}>
                    <Text>为产品维护迭代版本、业务模块、Git 资源和相关系统。</Text>
                    <Button disabled={!listState.rows.length} onClick={openFirstProductConfig} size="small">
                      配置当前页第一个产品
                    </Button>
                  </Space>
                ),
                title: '2. 补齐交付结构和代码资源',
              },
              {
                content: (
                  <Space orientation="vertical" size={6}>
                    <Text>创建知识空间和目录，上传产品文档，确保 RAG 检索有产品归属。</Text>
                    <Button onClick={() => navigateTo('/assets/knowledge')} size="small">
                      进入知识中心
                    </Button>
                  </Space>
                ),
                title: '3. 绑定知识空间',
              },
              {
                content: (
                  <Space orientation="vertical" size={6}>
                    <Text>安装并配置钉钉 MCP、代码仓库、内部数据源等插件连接。</Text>
                    <Button onClick={() => navigateTo('/tasks/plugins')} size="small">
                      进入插件管理
                    </Button>
                  </Space>
                ),
                title: '4. 配置插件连接',
              },
              {
                content: (
                  <Space orientation="vertical" size={6}>
                    <Text>在角色管理中按产品授予 read/write/admin scope，避免菜单可见但接口被拒绝。</Text>
                    <Button onClick={() => navigateTo('/system/roles')} size="small">
                      进入权限诊断
                    </Button>
                  </Space>
                ),
                title: '5. 校验角色与产品范围',
              },
              {
                content: (
                  <Space orientation="vertical" size={6}>
                    <Text>完成配置后到系统健康复检 SMTP、钉钉、MinIO、模型网关、知识质量和执行队列。</Text>
                    <Button onClick={() => navigateTo('/system/health')} size="small">
                      打开系统健康
                    </Button>
                  </Space>
                ),
                title: '6. 复检平台运行状态',
              },
            ]}
          />
        </Space>
      </Modal>
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
            <Input.TextArea rows={3} />
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
            toolBarRender={() =>
              canManageProducts
                ? [
                    <Button
                      aria-label="新增版本"
                      icon={<PlusOutlined />}
                      key="add-version"
                      onClick={() => openResourceEditor('version')}
                    >
                      新增版本
                    </Button>,
                  ]
                : []
            }
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
            toolBarRender={() =>
              canManageProducts
                ? [
                    <Button
                      aria-label="新增模块"
                      icon={<PlusOutlined />}
                      key="add-module"
                      onClick={() => openResourceEditor('module')}
                    >
                      新增模块
                    </Button>,
                  ]
                : []
            }
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
            toolBarRender={() =>
              canManageProducts
                ? [
                    <Button
                      aria-label="新增 Git 资源"
                      icon={<PlusOutlined />}
                      key="add-repository"
                      onClick={() => openResourceEditor('repository')}
                    >
                      新增 Git 资源
                    </Button>,
                  ]
                : []
            }
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
            toolBarRender={() =>
              canManageProducts
                ? [
                    <Button
                      aria-label="新增相关系统"
                      icon={<PlusOutlined />}
                      key="add-related-system"
                      onClick={() => openResourceEditor('relatedSystem')}
                    >
                      新增相关系统
                    </Button>,
                  ]
                : []
            }
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
              {resourceEditor.record ? null : (
                <Form.Item label="状态" name="status" rules={[{ required: true, message: '请选择状态' }]}>
                  <Select options={versionCreateStatusOptions} />
                </Form.Item>
              )}
              <Form.Item label="开始时间" name="start_date">
                <DateStringPicker placeholder="请选择开始时间" />
              </Form.Item>
              <Form.Item label="计划发布时间" name="release_date">
                <DateStringPicker placeholder="请选择计划发布时间" />
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
              <Form.Item label="代码平台" name="git_provider" rules={[{ required: true, message: '请选择代码平台' }]}>
                <Select
                  options={[
                    { label: 'GitLab', value: 'gitlab' },
                    { label: 'GitHub', value: 'github' },
                  ]}
                />
              </Form.Item>
              <Form.Item
                extra="优先填写仓库克隆地址，系统会自动推导 Project Path。"
                label="Remote URL"
                name="remote_url"
                rules={[{ required: true, message: '请输入 Remote URL' }]}
              >
                <Input placeholder="https://gitlab.example.com/group/project.git" />
              </Form.Item>
              <Form.Item
                extra="可选；仅在 Remote URL 无法推导或需要覆盖时填写。"
                label="Project Path"
                name="project_path"
              >
                <Input placeholder="group/project" />
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
                <Input.TextArea rows={3} />
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
