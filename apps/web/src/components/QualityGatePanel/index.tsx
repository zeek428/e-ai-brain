import { Alert, Descriptions, Empty, Space, Table, Tag, Typography } from 'antd';

const { Text } = Typography;

type QualityGatePanelProps = {
  gate?: Record<string, unknown>;
};

const CHECK_LABELS: Record<string, string> = {
  ci_status: 'CI 状态',
  dependency_scan: '依赖漏洞扫描',
  diff_limit: '变更规模限制',
  lint: '代码规范检查',
  secret_scan: '凭据扫描',
  security_scan: '安全扫描',
  type_check: '类型检查',
  unit_test: '单元测试',
};

const STATUS_LABELS: Record<string, { color: string; label: string }> = {
  blocked: { color: 'error', label: '已阻断' },
  failed: { color: 'error', label: '未通过' },
  passed: { color: 'success', label: '已通过' },
  pending: { color: 'default', label: '待执行' },
  running: { color: 'processing', label: '执行中' },
  skipped: { color: 'default', label: '已跳过' },
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function records(value: unknown) {
  return Array.isArray(value) ? value.map(record).filter((item) => Object.keys(item).length) : [];
}

function display(value: unknown, fallback = '-') {
  return value === null || value === undefined || value === '' ? fallback : String(value);
}

function statusTag(value: unknown) {
  const status = String(value || 'pending');
  const config = STATUS_LABELS[status] ?? { color: 'default', label: status };
  return <Tag color={config.color}>{config.label}</Tag>;
}

export function QualityGatePanel({ gate }: QualityGatePanelProps) {
  if (!gate) {
    return <Empty description="该任务尚未执行独立质量门禁" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  const checks = records(gate.checks);
  const blockedReasons = records(gate.blocked_reasons);
  return (
    <Space className="agent-governance-panel" orientation="vertical" size={16} style={{ width: '100%' }}>
      <Alert
        description={blockedReasons.length
          ? blockedReasons.map((reason) => display(reason.message ?? reason.code)).join('；')
          : '平台独立验证结果满足当前门禁策略。'}
        showIcon
        title={display(gate.summary, '质量门禁状态')}
        type={gate.status === 'passed' ? 'success' : gate.status === 'running' ? 'info' : 'error'}
      />
      <Descriptions bordered column={{ xs: 1, sm: 2, md: 3 }} size="small">
        <Descriptions.Item label="门禁编号">{display(gate.id)}</Descriptions.Item>
        <Descriptions.Item label="阶段">{gate.phase === 'pre_merge' ? '合并前' : display(gate.phase)}</Descriptions.Item>
        <Descriptions.Item label="状态">{statusTag(gate.status)}</Descriptions.Item>
        <Descriptions.Item label="风险等级">{display(gate.risk_level)}</Descriptions.Item>
        <Descriptions.Item label="独立证据数">{display(gate.independent_evidence_count, '0')}</Descriptions.Item>
        <Descriptions.Item label="上下文清单">{display(gate.context_manifest_id)}</Descriptions.Item>
      </Descriptions>
      <Table<Record<string, unknown>>
        columns={[
          {
            dataIndex: 'check_type',
            render: (value) => <Text strong>{CHECK_LABELS[String(value)] ?? display(value)}</Text>,
            title: '检查项',
            width: 150,
          },
          {
            dataIndex: 'status',
            render: statusTag,
            title: '结果',
            width: 100,
          },
          {
            key: 'evidence_source',
            render: (_, row) => row.independent ? <Tag color="blue">平台独立证据</Tag> : <Tag>Runner 自报</Tag>,
            title: '证据来源',
            width: 140,
          },
          {
            dataIndex: 'summary',
            render: (value) => display(value),
            title: '摘要',
          },
          {
            dataIndex: 'evidence_ref',
            ellipsis: true,
            render: (value) => <Text code>{display(value)}</Text>,
            title: '证据引用',
            width: 230,
          },
        ]}
        dataSource={checks}
        locale={{ emptyText: '门禁检查项尚未生成' }}
        pagination={false}
        rowKey={(row) => display(row.id ?? `${row.check_type}-${row.evidence_ref}`)}
        scroll={{ x: 850 }}
        size="small"
      />
    </Space>
  );
}
