import {
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import {
  Button,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
  Space,
  Switch,
  Typography,
} from 'antd';
import { useMemo, useState } from 'react';

import type {
  KnowledgeProcessingProfileRecord,
  KnowledgeStalenessRecord,
  KnowledgeStalenessSummary,
} from '../../../services/aiBrain';
import { StatusTag } from '../../../components/ManagementListPage';

const { Text } = Typography;

export type KnowledgeProcessingProfileFormValues = {
  capabilities: string[];
  credential_ref?: string;
  endpoint_url?: string;
  name: string;
  provider_type: string;
  stale_after_days?: number;
};

type KnowledgeProcessingGovernancePanelProps = {
  loading: boolean;
  onCreateProfile: (values: KnowledgeProcessingProfileFormValues) => Promise<void>;
  onRefresh: () => void;
  onScanStaleness: () => Promise<void>;
  onToggleProfile: (profile: KnowledgeProcessingProfileRecord, enabled: boolean) => Promise<void>;
  profiles: KnowledgeProcessingProfileRecord[];
  scanning: boolean;
  stalenessItems: KnowledgeStalenessRecord[];
  stalenessSummary: KnowledgeStalenessSummary;
};

const freshnessLabels: Record<string, { color: string; label: string }> = {
  expired: { color: 'red', label: '已过期' },
  expiring: { color: 'gold', label: '即将过期' },
  flagged_outdated: { color: 'orange', label: '被标记过期' },
  fresh: { color: 'green', label: '有效' },
};

const providerLabels: Record<string, string> = {
  builtin: '内置解析',
  gotenberg: 'Gotenberg',
  http: 'HTTP Provider',
  mineru: 'MinerU',
  multimodal_gateway: '多模态网关',
  paddleocr: 'PaddleOCR',
};

const capabilityLabels: Record<string, string> = {
  image_embedding: '图片向量',
  layout: '版面识别',
  ocr: 'OCR',
  table: '表格解析',
};

export function KnowledgeProcessingGovernancePanel({
  loading,
  onCreateProfile,
  onRefresh,
  onScanStaleness,
  onToggleProfile,
  profiles,
  scanning,
  stalenessItems,
  stalenessSummary,
}: KnowledgeProcessingGovernancePanelProps) {
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form] = Form.useForm<KnowledgeProcessingProfileFormValues>();
  const providerType = Form.useWatch('provider_type', form);

  const profileColumns = useMemo<ProColumns<KnowledgeProcessingProfileRecord>[]>(
    () => [
      { dataIndex: 'name', title: '配置名称', width: 180 },
      {
        dataIndex: 'providerType',
        render: (_, row) => providerLabels[row.providerType] ?? row.providerType,
        title: 'Provider',
        width: 150,
      },
      {
        dataIndex: 'capabilities',
        render: (_, row) => row.capabilities
          .map((capability) => capabilityLabels[capability] ?? capability)
          .join(' / ') || '-',
        title: '能力',
        width: 260,
      },
      {
        dataIndex: 'credentialRef',
        render: (_, row) => row.credentialRef || '-',
        title: '凭据引用',
        width: 220,
      },
      {
        dataIndex: 'version',
        render: (_, row) => `v${row.version}`,
        title: '配置版本',
        width: 100,
      },
      {
        dataIndex: 'status',
        render: (_, row) => (
          <Switch
            checked={row.status === 'active'}
            checkedChildren="启用"
            onChange={(checked) => {
              void onToggleProfile(row, checked).catch((error) => {
                message.error(error instanceof Error ? error.message : '处理配置更新失败');
              });
            }}
            unCheckedChildren="停用"
          />
        ),
        title: '状态',
        width: 110,
      },
    ],
    [onToggleProfile],
  );

  const stalenessColumns = useMemo<ProColumns<KnowledgeStalenessRecord>[]>(
    () => [
      { dataIndex: 'documentTitle', title: '文档', width: 220 },
      {
        dataIndex: 'version',
        render: (_, row) => `v${row.version}`,
        title: '版本',
        width: 80,
      },
      {
        dataIndex: 'freshnessStatus',
        render: (_, row) => {
          const status = freshnessLabels[row.freshnessStatus] ?? {
            color: 'default',
            label: row.freshnessStatus,
          };
          return <StatusTag color={status.color} label={status.label} />;
        },
        title: '有效性',
        width: 120,
      },
      { dataIndex: 'expiresAt', title: '过期时间', width: 180 },
      {
        dataIndex: 'outdatedFeedbackCount',
        title: '过期反馈',
        width: 100,
      },
    ],
    [],
  );

  const handleCreate = async (values: KnowledgeProcessingProfileFormValues) => {
    setCreating(true);
    try {
      await onCreateProfile(values);
      setCreateOpen(false);
      form.resetFields();
    } catch (error) {
      message.error(error instanceof Error ? error.message : '处理配置创建失败');
    } finally {
      setCreating(false);
    }
  };

  return (
    <section aria-label="多模态知识治理" className="knowledge-tab-panel">
      <div className="knowledge-panel-header">
        <Space orientation="vertical" size={2}>
          <Text strong>多模态与版本治理</Text>
          <Space wrap>
            <StatusTag color="green" label={`有效 ${stalenessSummary.fresh}`} />
            <StatusTag color="gold" label={`即将过期 ${stalenessSummary.expiring}`} />
            <StatusTag color="orange" label={`反馈过期 ${stalenessSummary.flaggedOutdated}`} />
            <StatusTag color="red" label={`已过期 ${stalenessSummary.expired}`} />
          </Space>
        </Space>
        <Space wrap>
          <Button icon={<ReloadOutlined />} loading={loading} onClick={onRefresh}>
            刷新
          </Button>
          <Button
            icon={<SafetyCertificateOutlined />}
            loading={scanning}
            onClick={() => void onScanStaleness()}
          >
            扫描过期
          </Button>
          <Button icon={<PlusOutlined />} onClick={() => setCreateOpen(true)} type="primary">
            新增处理配置
          </Button>
        </Space>
      </div>

      <Text strong>处理配置</Text>
      <ProTable<KnowledgeProcessingProfileRecord>
        columns={profileColumns}
        dataSource={profiles}
        loading={loading}
        options={false}
        pagination={false}
        rowKey="id"
        scroll={{ x: 1020 }}
        search={false}
        tableLayout="fixed"
      />

      <Text strong>文档有效性</Text>
      <ProTable<KnowledgeStalenessRecord>
        columns={stalenessColumns}
        dataSource={stalenessItems}
        loading={loading}
        options={false}
        pagination={false}
        rowKey="documentVersionId"
        scroll={{ x: 760 }}
        search={false}
        tableLayout="fixed"
      />

      <Modal
        confirmLoading={creating}
        destroyOnHidden
        onCancel={() => setCreateOpen(false)}
        onOk={() => form.submit()}
        open={createOpen}
        title="新增知识处理配置"
      >
        <Form<KnowledgeProcessingProfileFormValues>
          form={form}
          initialValues={{ capabilities: ['ocr', 'layout', 'table'], provider_type: 'multimodal_gateway' }}
          layout="vertical"
          onFinish={(values) => void handleCreate(values)}
        >
          <Form.Item label="配置名称" name="name" rules={[{ required: true, message: '请输入配置名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Provider" name="provider_type" rules={[{ required: true }]}>
            <Select
              options={Object.entries(providerLabels).map(([value, label]) => ({ label, value }))}
            />
          </Form.Item>
          {providerType !== 'builtin' ? (
            <Form.Item label="服务地址" name="endpoint_url" rules={[{ required: true, message: '请输入服务地址' }]}>
              <Input placeholder="https://vision.example.com/process" />
            </Form.Item>
          ) : null}
          <Form.Item label="凭据引用" name="credential_ref">
            <Input.Password placeholder="env:MULTIMODAL_GATEWAY_TOKEN" />
          </Form.Item>
          <Form.Item label="能力" name="capabilities" rules={[{ required: true }]}>
            <Select
              mode="multiple"
              options={[
                { label: 'OCR', value: 'ocr' },
                { label: '版面识别', value: 'layout' },
                { label: '表格解析', value: 'table' },
                { label: '图片向量', value: 'image_embedding' },
              ]}
            />
          </Form.Item>
          <Form.Item label="有效天数" name="stale_after_days">
            <InputNumber min={1} max={3650} precision={0} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}
