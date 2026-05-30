import { useState } from 'react';
import { PageContainer, ProCard, ProTable, StatisticCard } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Button, Col, Row, Space, Tag, Typography } from 'antd';

import { phases, taskRows, type TaskRow } from '../../data/workbench';
import { runMvpWorkflow, type MvpWorkflowResult } from '../../services/aiBrain';

const { Paragraph, Text, Title } = Typography;

type DemoState =
  | { status: 'idle' }
  | { status: 'running' }
  | ({ status: 'ready' } & MvpWorkflowResult)
  | { status: 'error'; message: string };

const columns: ProColumns<TaskRow>[] = [
  {
    title: '任务类型',
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
  const [demoState, setDemoState] = useState<DemoState>({ status: 'idle' });

  async function runDemo() {
    setDemoState({ status: 'running' });
    try {
      const result = await runMvpWorkflow();
      setDemoState({ status: 'ready', ...result });
    } catch (error) {
      setDemoState({
        status: 'error',
        message: error instanceof Error ? error.message : 'API workflow failed',
      });
    }
  }

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
        <ProCard
          title="任务列表"
          extra={
            <Button loading={demoState.status === 'running'} onClick={() => void runDemo()} type="primary">
              运行 MVP 演示流程
            </Button>
          }
        >
          {demoState.status !== 'idle' ? (
            <div className="demo-flow" aria-live="polite">
              {demoState.status === 'running' ? <Text>正在执行 API 工作流...</Text> : null}
              {demoState.status === 'error' ? <Text type="danger">{demoState.message}</Text> : null}
              {demoState.status === 'ready' ? (
                <div className="demo-result">
                  <span>
                    需求 <strong>{demoState.requirementId}</strong>
                  </span>
                  <span>
                    任务 <strong>{demoState.taskId}</strong>
                  </span>
                  <span>
                    Review <strong>{demoState.reviewId}</strong>
                  </span>
                  <Tag color="blue">{demoState.taskStatus}</Tag>
                  <Tag color="gold">{demoState.currentStep}</Tag>
                  <Tag color="green">下游关系 {demoState.downstreamCount}</Tag>
                  <Tag color={demoState.riskCount > 0 ? 'orange' : 'default'}>
                    风险 {demoState.riskCount}
                  </Tag>
                </div>
              ) : null}
            </div>
          ) : null}
          <ProTable<TaskRow>
            columns={columns}
            dataSource={taskRows}
            options={false}
            pagination={false}
            rowKey="type"
            search={false}
          />
        </ProCard>

        <ProCard title="确认台">
          <Paragraph>待确认项会显示需求快照、产品上下文、检索证据、AI 输出和审计轨迹。</Paragraph>
          <StatisticCard.Group direction="column">
            <StatisticCard
              statistic={{
                description: 'version=1，提交确认时使用乐观锁避免并发覆盖。',
                prefix: <Tag color="gold">pending</Tag>,
                title: '产品详细设计确认',
                value: 'waiting_review',
              }}
            />
          </StatisticCard.Group>
        </ProCard>
      </section>
    </PageContainer>
  );
}
