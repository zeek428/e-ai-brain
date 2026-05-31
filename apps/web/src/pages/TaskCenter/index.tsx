import { PageContainer, ProCard, ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import { Alert, Button, Col, Input, Modal, Row, Space, Tag, Typography, message } from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { phases } from '../../data/workbench';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  approveTaskCenterReview,
  createTechnicalSolutionTask,
  fetchTaskMarkdown,
  fetchTaskCenterPendingReviews,
  fetchTaskCenterTasks,
  startTaskCenterTask,
  type TaskCenterReviewRecord,
  type TaskCenterTaskRecord,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

const { Paragraph, Text, Title } = Typography;

export default function TaskCenterPage() {
  const [markdownPreview, setMarkdownPreview] = useState<{
    content: string;
    title: string;
  }>();
  const {
    error,
    reload: reloadTasks,
    rows: dataSource,
    status,
  } = useRemoteRows(fetchTaskCenterTasks);
  const {
    error: reviewsError,
    reload: reloadReviews,
    rows: reviewRows,
    status: reviewsStatus,
  } = useRemoteRows(fetchTaskCenterPendingReviews);

  const reloadTaskCenter = useCallback(async () => {
    await Promise.all([reloadTasks(), reloadReviews()]);
  }, [reloadReviews, reloadTasks]);

  const handleStartTask = useCallback(async (task: TaskCenterTaskRecord) => {
    try {
      await startTaskCenterTask(task.id);
      message.success('任务已启动，已进入人工确认');
      await reloadTaskCenter();
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, [reloadTaskCenter]);

  const handleApproveReview = useCallback(async (review: TaskCenterReviewRecord) => {
    try {
      await approveTaskCenterReview(review.id, review.version);
      message.success('确认已提交，任务已完成');
      await reloadTaskCenter();
    } catch (reviewError) {
      message.error(formatMutationError(reviewError));
    }
  }, [reloadTaskCenter]);

  const handleCreateTechnicalSolution = useCallback(async (task: TaskCenterTaskRecord) => {
    try {
      await createTechnicalSolutionTask(task);
      message.success('技术方案任务已创建');
      await reloadTaskCenter();
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, [reloadTaskCenter]);

  const handleExportMarkdown = useCallback(async (task: TaskCenterTaskRecord) => {
    try {
      const content = await fetchTaskMarkdown(task.id);
      setMarkdownPreview({ content, title: task.label });
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, []);

  const columns = useMemo<ProColumns<TaskCenterTaskRecord>[]>(
    () => [
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
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            {row.status === 'draft' ? (
              <Button onClick={() => handleStartTask(row)} type="link">
                启动任务
              </Button>
            ) : null}
            {row.type === 'product_detail_design' && row.status === 'completed' ? (
              <Button onClick={() => handleCreateTechnicalSolution(row)} type="link">
                生成技术方案
              </Button>
            ) : null}
            {row.type === 'technical_solution' && row.status === 'completed' ? (
              <Button onClick={() => handleExportMarkdown(row)} type="link">
                导出 Markdown
              </Button>
            ) : null}
          </Space>
        ),
      },
    ],
    [handleCreateTechnicalSolution, handleExportMarkdown, handleStartTask],
  );

  const reviewColumns = useMemo<ProColumns<TaskCenterReviewRecord>[]>(
    () => [
      {
        dataIndex: 'id',
        title: '确认编号',
      },
      {
        dataIndex: 'stage',
        title: '确认阶段',
      },
      {
        dataIndex: 'contentSummary',
        title: 'AI 输出摘要',
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) => <Tag color="gold">{row.status}</Tag>,
      },
      {
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Button onClick={() => handleApproveReview(row)} type="link">
            确认通过
          </Button>
        ),
      },
    ],
    [handleApproveReview],
  );

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
          {reviewsError ? (
            <Alert className="management-list-alert" showIcon title={formatRemoteRowsError(reviewsError)} type="error" />
          ) : null}
          <Paragraph>待确认项来自 Review 接口，确认后任务进入完成状态并生成知识沉淀候选。</Paragraph>
          <ProTable<TaskCenterReviewRecord>
            columns={reviewColumns}
            dataSource={reviewRows}
            loading={reviewsStatus === 'loading'}
            options={false}
            pagination={false}
            rowKey="id"
            search={false}
          />
          {reviewRows.length === 0 && reviewsStatus === 'ready' ? (
            <Text type="secondary">当前没有待确认项。</Text>
          ) : null}
        </ProCard>
      </section>

      <Modal
        footer={null}
        onCancel={() => setMarkdownPreview(undefined)}
        open={Boolean(markdownPreview)}
        title={markdownPreview?.title ? `Markdown 导出：${markdownPreview.title}` : 'Markdown 导出'}
        width={760}
      >
        <Input.TextArea
          autoSize={{ maxRows: 22, minRows: 12 }}
          readOnly
          value={markdownPreview?.content}
        />
      </Modal>
    </PageContainer>
  );
}
