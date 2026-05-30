import { DeleteOutlined, EditOutlined } from '@ant-design/icons';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Form, Input, Modal, Popconfirm, Select, Space, message } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import { knowledgeRows, type KnowledgeRecord } from '../../data/management';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  createManagementKnowledgeDocument,
  deleteManagementKnowledgeDocument,
  fetchManagementKnowledge,
  updateManagementKnowledgeDocument,
} from '../../services/aiBrain';
import {
  formatMutationError,
  joinTextList,
  splitCommaText,
} from '../../utils/managementCrud';

const statusLabels: Record<KnowledgeRecord['status'], { color: string; label: string }> = {
  failed: { color: 'red', label: '索引失败' },
  indexed: { color: 'green', label: '已索引' },
  pending_index: { color: 'gold', label: '待索引' },
  review_pending: { color: 'blue', label: '待审核' },
};

type KnowledgeFormValues = {
  content: string;
  doc_type: string;
  index_status?: KnowledgeRecord['status'];
  permission_roles?: string;
  tags?: string;
  title: string;
};

export default function KnowledgePage() {
  const [form] = Form.useForm<KnowledgeFormValues>();
  const [editingDocument, setEditingDocument] = useState<KnowledgeRecord | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const {
    error,
    reload,
    rows: dataSource,
    status,
  } = useRemoteRows(knowledgeRows, fetchManagementKnowledge);

  const openCreateModal = () => {
    setEditingDocument(null);
    form.resetFields();
    form.setFieldsValue({
      doc_type: 'manual',
      permission_roles: 'admin',
    });
    setIsModalOpen(true);
  };

  const openEditModal = useCallback((row: KnowledgeRecord) => {
    setEditingDocument(row);
    form.setFieldsValue({
      content: row.content ?? '',
      doc_type: row.documentType,
      index_status: row.status,
      permission_roles: joinTextList(row.permissionRoles) || row.ownerRole,
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
      permission_roles: splitCommaText(values.permission_roles),
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
      await reload();
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

  const columns = useMemo<ProColumns<KnowledgeRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        title: '知识编号',
      },
      {
        dataIndex: 'title',
        title: '知识标题',
      },
      {
        dataIndex: 'documentType',
        title: '类型',
      },
      {
        dataIndex: 'ownerRole',
        title: '权限角色',
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
        dataIndex: 'updatedAt',
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
            <Popconfirm okText="删除" onConfirm={() => handleDelete(row)} title={`删除知识 ${row.id}？`}>
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
      <ManagementListPage<KnowledgeRecord>
        breadcrumbGroup="产品资产"
        columns={columns}
        dataSource={dataSource}
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
              { label: '待索引', value: 'pending_index' },
              { label: '待审核', value: 'review_pending' },
              { label: '索引失败', value: 'failed' },
            ],
            type: 'select',
          },
        ]}
        loading={status === 'loading'}
        notice={formatRemoteRowsError(error)}
        onPrimaryAction={openCreateModal}
        onReload={() => void reload()}
        primaryAction="导入文档"
        rowKey="id"
        tableTitle="知识列表"
        title="知识中心"
      />
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
          <Form.Item label="权限角色" name="permission_roles">
            <Input placeholder="admin, knowledge_owner" />
          </Form.Item>
          <Form.Item label="标签" name="tags">
            <Input />
          </Form.Item>
          {editingDocument ? (
            <Form.Item label="索引状态" name="index_status">
              <Select
                options={[
                  { label: '已索引', value: 'indexed' },
                  { label: '待索引', value: 'pending_index' },
                  { label: '待审核', value: 'review_pending' },
                  { label: '索引失败', value: 'failed' },
                ]}
              />
            </Form.Item>
          ) : null}
          <Form.Item label="内容" name="content" rules={[{ required: true, message: '请输入知识内容' }]}>
            <Input.TextArea autoSize={{ minRows: 5 }} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
