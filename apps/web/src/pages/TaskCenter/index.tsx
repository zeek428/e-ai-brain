import { PageContainer, ProCard, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Alert, Col, Row, Space, Tag, Typography } from 'antd';

import { phases } from '../../data/workbench';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import { fetchTaskCenterTasks, type TaskCenterTaskRecord } from '../../services/aiBrain';

const { Paragraph, Text, Title } = Typography;

const columns: ProColumns<TaskCenterTaskRecord>[] = [
  {
    title: '任务',
    dataIndex: 'label',
    key: 'label',
    render: (_value, row) => (
      <span className="task-name">
        <strong>{row.label}</strong>
        <small>{row.type}</small>
      </span>
    ),
  },
  {
    title: '状态',
    dataIndex: 'status',
    key: 'status',
    render: (_, row) => <Tag color="blue">{row.status}</Tag>,
  },
  {
    title: '负责人',
    dataIndex: 'owner',
    key: 'owner',
  },
];

export default function TaskCenterPage() {
  const { error, rows: dataSource, status } = useRemoteRows(fetchTaskCenterTasks);

  return (
    <PageContainer title={false}>
      <Row className="phase-grid" gutter={[16, 16]}>
        {phases.map((phase) => (
          <Col key={phase.name} lg={8} md={12} xs={24}>
            <ProCard className="phase-card">
              <Space orientation="vertical" size={8}>
                <Tag color={phase.state === 'active' ? 'blue' : 'default'}>
                  {phase.state === 'active' ? '当前' : phase.state === 'next' ? '下一步' : '随后'}
                </Tag>
                <Title level={2}>{phase.name}</Title>
                <Paragraph>{phase.scope}</Paragraph>
              </Space>
            </ProCard>
          </Col>
        ))}
      </Row>

      <section className="workspace-grid">
        <ProCard title="任务列表">
          {error ? <Alert className="management-list-alert" showIcon title={formatRemoteRowsError(error)} type="error" /> : null}
          <ProTable<TaskCenterTaskRecord>
            columns={columns}
            dataSource={dataSource}
            loading={status === 'loading'}
            options={false}
            pagination={false}
            rowKey="id"
            search={false}
          />
        </ProCard>

        <ProCard title="确认台">
          <Paragraph>待确认项会显示需求快照、产品上下文、检索证据、AI 输出和审计轨迹。</Paragraph>
          <Text type="secondary">待确认数据将从 Review 接口加载。</Text>
        </ProCard>
      </section>
    </PageContainer>
  );
}
