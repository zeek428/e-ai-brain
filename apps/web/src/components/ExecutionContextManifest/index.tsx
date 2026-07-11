import { Descriptions, Empty, Space, Table, Tag, Typography } from 'antd';

const { Text } = Typography;

type ExecutionContextManifestProps = {
  manifest?: Record<string, unknown>;
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function records(value: unknown) {
  return Array.isArray(value) ? value.map(record).filter((item) => Object.keys(item).length) : [];
}

function strings(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item ?? '').trim()).filter(Boolean) : [];
}

function display(value: unknown, fallback = '-') {
  return value === null || value === undefined || value === '' ? fallback : String(value);
}

function refTitle(item: Record<string, unknown>) {
  return display(item.title ?? item.name ?? item.id ?? item.code);
}

export function ExecutionContextManifest({ manifest }: ExecutionContextManifestProps) {
  if (!manifest) {
    return <Empty description="该任务尚未生成执行上下文清单" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }
  const repository = record(manifest.repository_ref);
  const acceptanceCriteria = strings(manifest.acceptance_criteria);
  const requirements = records(manifest.requirement_refs);
  const bugs = records(manifest.bug_refs);
  const knowledge = records(manifest.knowledge_refs);
  const truncation = record(manifest.truncation_summary);
  return (
    <Space className="agent-governance-panel" orientation="vertical" size={16} style={{ width: '100%' }}>
      <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small">
        <Descriptions.Item label="清单编号">{display(manifest.id)}</Descriptions.Item>
        <Descriptions.Item label="上下文版本">v{display(manifest.version, '1')}</Descriptions.Item>
        <Descriptions.Item label="代码库">{display(repository.name ?? repository.id)}</Descriptions.Item>
        <Descriptions.Item label="分支">{display(manifest.branch)}</Descriptions.Item>
        <Descriptions.Item label="Remote URL" span={2}>
          <Text code>{display(repository.remote_url ?? repository.url)}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="内容哈希" span={2}>
          <Text code copyable={Boolean(manifest.content_hash)}>{display(manifest.content_hash)}</Text>
        </Descriptions.Item>
      </Descriptions>

      <section className="agent-governance-section">
        <Text strong>验收标准</Text>
        {acceptanceCriteria.length ? (
          <ol>{acceptanceCriteria.map((criterion) => <li key={criterion}>{criterion}</li>)}</ol>
        ) : <Text type="secondary">未携带验收标准</Text>}
      </section>

      <section className="agent-governance-section">
        <Text strong>业务来源</Text>
        <div className="agent-governance-reference-list">
          {requirements.map((item) => (
            <div key={`requirement-${display(item.id ?? refTitle(item))}`}>
              <Tag color="blue">需求</Tag><Text>{refTitle(item)}</Text>
            </div>
          ))}
          {bugs.map((item) => (
            <div key={`bug-${display(item.id ?? refTitle(item))}`}>
              <Tag color="red">Bug</Tag><Text>{refTitle(item)}</Text>
            </div>
          ))}
          {!requirements.length && !bugs.length ? <Text type="secondary">未携带需求或 Bug 快照</Text> : null}
        </div>
      </section>

      <section className="agent-governance-section">
        <Space size={8} wrap>
          <Text strong>知识引用</Text>
          <Tag>{knowledge.length} 份</Tag>
          <Tag color={Number(truncation.truncated_knowledge_count || 0) > 0 ? 'gold' : 'green'}>
            截断 {display(truncation.truncated_knowledge_count, '0')} 份
          </Tag>
        </Space>
        <Table<Record<string, unknown>>
          columns={[
            { key: 'title', render: (_, row) => <Text strong>{refTitle(row)}</Text>, title: '文档' },
            { dataIndex: 'document_version', render: (value) => `v${display(value, '1')}`, title: '版本', width: 90 },
            { dataIndex: 'retrieval_reason', render: (value) => display(value), title: '召回原因', width: 260 },
            {
              dataIndex: 'content_truncated',
              render: (value) => value ? <Tag color="gold">已截断</Tag> : <Tag color="green">完整摘要</Tag>,
              title: '内容状态',
              width: 110,
            },
          ]}
          dataSource={knowledge}
          locale={{ emptyText: '本次执行未召回知识文档' }}
          pagination={false}
          rowKey={(row) => display(row.chunk_id ?? row.document_id ?? refTitle(row))}
          scroll={{ x: 700 }}
          size="small"
        />
      </section>
    </Space>
  );
}
