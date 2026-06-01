import { MoreOutlined } from '@ant-design/icons';
import { ProTable } from '@ant-design/pro-components';
import type { ProColumns } from '@ant-design/pro-components';
import {
  Alert,
  Button,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Tag,
  Typography,
  message,
} from 'antd';
import { useCallback, useMemo, useState } from 'react';

import { ManagementListPage, StatusTag } from '../../components/ManagementListPage';
import { formatRemoteRowsError, useRemoteRows } from '../../hooks/useRemoteRows';
import {
  approveTaskCenterReview,
  createAutomatedTestingTask,
  createCodeReviewTask,
  createDevelopmentPlanningTask,
  createTechnicalSolutionTask,
  createTaskWritebackResult,
  fetchCodeReviewReport,
  fetchProductGitRepositories,
  fetchTaskMarkdown,
  fetchTaskCenterPendingReviews,
  fetchTaskCenterTasks,
  fetchTaskWritebackResult,
  previewGitLabMergeRequest,
  requestTaskCenterReviewMoreInfo,
  snapshotGitLabMergeRequest,
  type CodeReviewReportRecord,
  type GitLabMergeRequestPreview,
  type ProductGitRepositoryOption,
  type TaskWritebackResultRecord,
  startTaskCenterTask,
  submitTaskCenterMoreInfo,
  type TaskCenterReviewRecord,
  type TaskCenterTaskRecord,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';

const { Paragraph, Text } = Typography;

const taskStatusLabels: Record<string, { color: string; label: string }> = {
  cancelled: { color: 'default', label: '已取消' },
  completed: { color: 'green', label: '已完成' },
  draft: { color: 'default', label: '草稿' },
  failed: { color: 'red', label: '失败' },
  running: { color: 'blue', label: '运行中' },
  waiting_more_info: { color: 'orange', label: '待补充' },
  waiting_review: { color: 'gold', label: '待确认' },
  writing_back: { color: 'purple', label: '写回中' },
};

const taskTypeLabels: Record<string, string> = {
  automated_testing: '自动化测试',
  code_review: 'Code Review',
  development_planning: '开发计划',
  product_detail_design: '产品详细设计',
  technical_solution: '技术方案',
};

const writebackStatusLabels: Record<string, { color: string; label: string }> = {
  completed: { color: 'green', label: '已生成' },
  failed: { color: 'red', label: '失败' },
  not_written: { color: 'default', label: '未写回' },
};

type TaskActionItem = {
  key: string;
  label: string;
  onClick: () => void;
  type?: 'default' | 'primary';
};

type RequestMoreInfoFormValues = {
  questions: string;
};

type SubmitMoreInfoFormValues = {
  answer: string;
};

function splitTextLines(value: string) {
  return value
    .split('\n')
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatFinding(finding: unknown, index: number) {
  if (!finding || typeof finding !== 'object' || Array.isArray(finding)) {
    return `${index + 1}. ${String(finding ?? '-')}`;
  }
  const item = finding as Record<string, unknown>;
  const location = [item.file_path, item.line_start ? `:${item.line_start}` : undefined]
    .filter(Boolean)
    .join('');
  const summary = item.message ?? item.summary ?? item.suggestion ?? JSON.stringify(item);
  return `${index + 1}. ${[item.severity, location, summary].filter(Boolean).join(' · ')}`;
}

export default function TaskCenterPage() {
  const [requestMoreInfoForm] = Form.useForm<RequestMoreInfoFormValues>();
  const [submitMoreInfoForm] = Form.useForm<SubmitMoreInfoFormValues>();
  const [markdownPreview, setMarkdownPreview] = useState<{
    content: string;
    title: string;
  }>();
  const [codeReviewDraft, setCodeReviewDraft] = useState<{
    loading: boolean;
    mrIid: number;
    preview?: GitLabMergeRequestPreview;
    repositories: ProductGitRepositoryOption[];
    repositoryId?: string;
    submitting: boolean;
    task: TaskCenterTaskRecord;
  }>();
  const [codeReviewReport, setCodeReviewReport] = useState<{
    loading: boolean;
    report?: CodeReviewReportRecord;
    task: TaskCenterTaskRecord;
  }>();
  const [writebackDialog, setWritebackDialog] = useState<{
    loading: boolean;
    result?: TaskWritebackResultRecord;
    submitting: boolean;
    task: TaskCenterTaskRecord;
  }>();
  const [actionDialog, setActionDialog] = useState<{
    task: TaskCenterTaskRecord;
  }>();
  const [reviewDialog, setReviewDialog] = useState<{
    task?: TaskCenterTaskRecord;
  }>();
  const [requestMoreInfoDialog, setRequestMoreInfoDialog] = useState<{
    review: TaskCenterReviewRecord;
    submitting: boolean;
  }>();
  const [submitMoreInfoDialog, setSubmitMoreInfoDialog] = useState<{
    submitting: boolean;
    task: TaskCenterTaskRecord;
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

  const visibleReviewRows = useMemo(
    () =>
      reviewDialog?.task
        ? reviewRows.filter((review) => review.aiTaskId === reviewDialog.task?.id)
        : reviewRows,
    [reviewDialog, reviewRows],
  );
  const selectedActionTask = actionDialog?.task;

  const openReviewDialog = useCallback((task?: TaskCenterTaskRecord) => {
    setReviewDialog({ task });
    void reloadReviews();
  }, [reloadReviews]);

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
      setReviewDialog(undefined);
      await reloadTaskCenter();
    } catch (reviewError) {
      message.error(formatMutationError(reviewError));
    }
  }, [reloadTaskCenter]);

  const openRequestMoreInfoDialog = useCallback((review: TaskCenterReviewRecord) => {
    requestMoreInfoForm.resetFields();
    setRequestMoreInfoDialog({ review, submitting: false });
  }, [requestMoreInfoForm]);

  const handleRequestMoreInfo = useCallback(async () => {
    if (!requestMoreInfoDialog) {
      return;
    }
    const values = await requestMoreInfoForm.validateFields();
    const questions = splitTextLines(values.questions);
    if (questions.length === 0) {
      requestMoreInfoForm.setFields([
        { errors: ['请输入需要补充的问题'], name: 'questions' },
      ]);
      return;
    }
    setRequestMoreInfoDialog((current) => (current ? { ...current, submitting: true } : current));
    try {
      await requestTaskCenterReviewMoreInfo(
        requestMoreInfoDialog.review.id,
        requestMoreInfoDialog.review.version,
        questions,
      );
      message.success('已要求补充信息');
      setRequestMoreInfoDialog(undefined);
      setReviewDialog(undefined);
      await reloadTaskCenter();
    } catch (reviewError) {
      setRequestMoreInfoDialog((current) => (current ? { ...current, submitting: false } : current));
      message.error(formatMutationError(reviewError));
    }
  }, [reloadTaskCenter, requestMoreInfoDialog, requestMoreInfoForm]);

  const openSubmitMoreInfoDialog = useCallback((task: TaskCenterTaskRecord) => {
    submitMoreInfoForm.resetFields();
    setSubmitMoreInfoDialog({ submitting: false, task });
  }, [submitMoreInfoForm]);

  const handleSubmitMoreInfo = useCallback(async () => {
    if (!submitMoreInfoDialog) {
      return;
    }
    const values = await submitMoreInfoForm.validateFields();
    const answer = values.answer.trim();
    if (!answer) {
      submitMoreInfoForm.setFields([
        { errors: ['请输入补充说明'], name: 'answer' },
      ]);
      return;
    }
    setSubmitMoreInfoDialog((current) => (current ? { ...current, submitting: true } : current));
    try {
      await submitTaskCenterMoreInfo(submitMoreInfoDialog.task.id, [
        { answer, question: '补充说明' },
      ]);
      message.success('补充信息已提交，任务已回到草稿');
      setSubmitMoreInfoDialog(undefined);
      await reloadTaskCenter();
    } catch (taskError) {
      setSubmitMoreInfoDialog((current) => (current ? { ...current, submitting: false } : current));
      message.error(formatMutationError(taskError));
    }
  }, [reloadTaskCenter, submitMoreInfoDialog, submitMoreInfoForm]);

  const handleCreateTechnicalSolution = useCallback(async (task: TaskCenterTaskRecord) => {
    try {
      await createTechnicalSolutionTask(task);
      message.success('技术方案任务已创建');
      await reloadTaskCenter();
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, [reloadTaskCenter]);

  const handleCreateDevelopmentPlanning = useCallback(async (task: TaskCenterTaskRecord) => {
    try {
      await createDevelopmentPlanningTask(task);
      message.success('开发计划任务已创建');
      await reloadTaskCenter();
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, [reloadTaskCenter]);

  const handleCreateAutomatedTesting = useCallback(async (task: TaskCenterTaskRecord) => {
    try {
      await createAutomatedTestingTask(task);
      message.success('自动化测试任务已创建');
      await reloadTaskCenter();
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, [reloadTaskCenter]);

  const handleOpenCodeReview = useCallback(async (task: TaskCenterTaskRecord) => {
    if (!task.productId) {
      message.error('缺少产品编号，无法加载产品 Git 仓库。');
      return;
    }
    setCodeReviewDraft({
      loading: true,
      mrIid: 1,
      repositories: [],
      submitting: false,
      task,
    });
    try {
      const repositories = await fetchProductGitRepositories(task.productId);
      setCodeReviewDraft((current) =>
        current?.task.id === task.id
          ? {
              ...current,
              loading: false,
              repositories,
              repositoryId: repositories[0]?.id,
            }
          : current,
      );
    } catch (taskError) {
      setCodeReviewDraft((current) =>
        current?.task.id === task.id ? { ...current, loading: false } : current,
      );
      message.error(formatMutationError(taskError));
    }
  }, []);

  const handlePreviewCodeReview = useCallback(async () => {
    if (!codeReviewDraft?.repositoryId) {
      message.error('请选择 GitLab 仓库。');
      return;
    }
    try {
      const preview = await previewGitLabMergeRequest(
        codeReviewDraft.repositoryId,
        codeReviewDraft.mrIid,
      );
      setCodeReviewDraft((current) => (current ? { ...current, preview } : current));
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, [codeReviewDraft]);

  const handleCreateCodeReview = useCallback(async () => {
    if (!codeReviewDraft?.repositoryId) {
      message.error('请选择 GitLab 仓库。');
      return;
    }
    if (!codeReviewDraft.task.requirementId) {
      message.error('缺少需求编号，无法创建 Code Review 任务。');
      return;
    }
    setCodeReviewDraft((current) => (current ? { ...current, submitting: true } : current));
    try {
      const snapshot = await snapshotGitLabMergeRequest({
        mrIid: codeReviewDraft.mrIid,
        repositoryId: codeReviewDraft.repositoryId,
        requirementId: codeReviewDraft.task.requirementId,
        technicalSolutionTaskId: codeReviewDraft.task.id,
      });
      await createCodeReviewTask(codeReviewDraft.task, snapshot.id, codeReviewDraft.mrIid);
      message.success('Code Review 任务已创建');
      setCodeReviewDraft(undefined);
      await reloadTaskCenter();
    } catch (taskError) {
      setCodeReviewDraft((current) => (current ? { ...current, submitting: false } : current));
      message.error(formatMutationError(taskError));
    }
  }, [codeReviewDraft, reloadTaskCenter]);

  const handleOpenCodeReviewReport = useCallback(async (task: TaskCenterTaskRecord) => {
    setCodeReviewReport({ loading: true, task });
    try {
      const report = await fetchCodeReviewReport(task.id);
      setCodeReviewReport((current) =>
        current?.task.id === task.id ? { ...current, loading: false, report } : current,
      );
    } catch (taskError) {
      setCodeReviewReport((current) =>
        current?.task.id === task.id ? { ...current, loading: false } : current,
      );
      message.error(formatMutationError(taskError));
    }
  }, []);

  const handleExportMarkdown = useCallback(async (task: TaskCenterTaskRecord) => {
    try {
      const content = await fetchTaskMarkdown(task.id);
      setMarkdownPreview({ content, title: task.label });
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, []);

  const handleOpenWriteback = useCallback(async (task: TaskCenterTaskRecord) => {
    setWritebackDialog({ loading: true, submitting: false, task });
    try {
      const result = await fetchTaskWritebackResult(task.id);
      setWritebackDialog((current) =>
        current?.task.id === task.id ? { ...current, loading: false, result } : current,
      );
    } catch (taskError) {
      setWritebackDialog((current) =>
        current?.task.id === task.id ? { ...current, loading: false } : current,
      );
      message.error(formatMutationError(taskError));
    }
  }, []);

  const handleCreateWriteback = useCallback(async () => {
    if (!writebackDialog?.task) {
      return;
    }
    const { task } = writebackDialog;
    setWritebackDialog((current) => (current ? { ...current, submitting: true } : current));
    try {
      const result = await createTaskWritebackResult(task.id);
      setWritebackDialog((current) =>
        current?.task.id === task.id
          ? { ...current, loading: false, result, submitting: false }
          : current,
      );
      message.success('模拟 Issue 已生成');
    } catch (taskError) {
      setWritebackDialog((current) => (current ? { ...current, submitting: false } : current));
      message.error(formatMutationError(taskError));
    }
  }, [writebackDialog]);

  const taskActionItems = useMemo<TaskActionItem[]>(() => {
    if (!selectedActionTask) {
      return [];
    }

    const closeAndRun =
      (action: () => void | Promise<void>) =>
      () => {
        setActionDialog(undefined);
        void action();
      };

    const actions: TaskActionItem[] = [];

    if (selectedActionTask.status === 'draft') {
      actions.push({
        key: 'start',
        label: '启动任务',
        onClick: closeAndRun(() => handleStartTask(selectedActionTask)),
        type: 'primary',
      });
    }

    if (selectedActionTask.status === 'waiting_review') {
      actions.push({
        key: 'review',
        label: '确认输出',
        onClick: closeAndRun(() => openReviewDialog(selectedActionTask)),
        type: 'primary',
      });
    }

    if (selectedActionTask.status === 'waiting_more_info') {
      actions.push({
        key: 'submit-more-info',
        label: '提交补充信息',
        onClick: closeAndRun(() => openSubmitMoreInfoDialog(selectedActionTask)),
        type: 'primary',
      });
    }

    if (
      selectedActionTask.type === 'product_detail_design' &&
      selectedActionTask.status === 'completed'
    ) {
      actions.push({
        key: 'create-solution',
        label: '生成技术方案',
        onClick: closeAndRun(() => handleCreateTechnicalSolution(selectedActionTask)),
        type: 'primary',
      });
    }

    if (
      selectedActionTask.type === 'technical_solution' &&
      selectedActionTask.status === 'completed'
    ) {
      actions.push(
        {
          key: 'create-development-planning',
          label: '生成开发计划',
          onClick: closeAndRun(() => handleCreateDevelopmentPlanning(selectedActionTask)),
          type: 'primary',
        },
        {
          key: 'create-automated-testing',
          label: '生成自动化测试',
          onClick: closeAndRun(() => handleCreateAutomatedTesting(selectedActionTask)),
        },
        {
          key: 'create-code-review',
          label: '创建 Code Review',
          onClick: closeAndRun(() => handleOpenCodeReview(selectedActionTask)),
        },
        {
          key: 'export-markdown',
          label: '导出 Markdown',
          onClick: closeAndRun(() => handleExportMarkdown(selectedActionTask)),
        },
      );
    }

    if (selectedActionTask.status === 'completed') {
      actions.push({
        key: 'writeback',
        label: '模拟 Issue',
        onClick: closeAndRun(() => handleOpenWriteback(selectedActionTask)),
      });
    }

    if (selectedActionTask.type === 'code_review') {
      actions.push({
        key: 'code-review-report',
        label: '查看报告',
        onClick: closeAndRun(() => handleOpenCodeReviewReport(selectedActionTask)),
      });
    }

    return actions;
  }, [
    handleCreateAutomatedTesting,
    handleCreateDevelopmentPlanning,
    handleCreateTechnicalSolution,
    handleExportMarkdown,
    handleOpenCodeReview,
    handleOpenCodeReviewReport,
    handleOpenWriteback,
    handleStartTask,
    openSubmitMoreInfoDialog,
    openReviewDialog,
    selectedActionTask,
  ]);

  const columns = useMemo<ProColumns<TaskCenterTaskRecord>[]>(
    () => [
      {
        title: '任务',
        dataIndex: 'label',
        key: 'label',
        render: (_value, row) => (
          <span className="task-name">
            <strong>{row.label}</strong>
            <small>{taskTypeLabels[row.type] ?? row.type}</small>
          </span>
        ),
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        render: (_, row) => {
          const statusLabel = taskStatusLabels[row.status] ?? { color: 'blue', label: row.status };
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
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
          <Button
            aria-label="操作"
            icon={<MoreOutlined />}
            onClick={() => setActionDialog({ task: row })}
            type="link"
          >
            操作
          </Button>
        ),
      },
    ],
    [],
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
          <Space size={4}>
            <Button onClick={() => handleApproveReview(row)} type="link">
              确认通过
            </Button>
            <Button onClick={() => openRequestMoreInfoDialog(row)} type="link">
              要求补充
            </Button>
          </Space>
        ),
      },
    ],
    [handleApproveReview, openRequestMoreInfoDialog],
  );

  return (
    <>
      <ManagementListPage<TaskCenterTaskRecord>
        breadcrumbGroup="任务中心"
        columns={columns}
        dataSource={dataSource}
        filters={[
          { label: '任务', name: 'label', type: 'text' },
          {
            label: '任务类型',
            name: 'type',
            options: [
              { label: '产品详细设计', value: 'product_detail_design' },
              { label: '技术方案', value: 'technical_solution' },
              { label: '开发计划', value: 'development_planning' },
              { label: '自动化测试', value: 'automated_testing' },
              { label: 'Code Review', value: 'code_review' },
            ],
            type: 'select',
          },
          {
            label: '状态',
            name: 'status',
            options: [
              { label: '草稿', value: 'draft' },
              { label: '运行中', value: 'running' },
              { label: '待补充', value: 'waiting_more_info' },
              { label: '待确认', value: 'waiting_review' },
              { label: '已完成', value: 'completed' },
              { label: '失败', value: 'failed' },
            ],
            type: 'select',
          },
          { label: '负责人', name: 'owner', type: 'text' },
        ]}
        loading={status === 'loading'}
        notice={formatRemoteRowsError(error ?? reviewsError)}
        onReload={() => void reloadTaskCenter()}
        rowKey="id"
        tableTitle="任务列表"
        title="任务管理"
        toolbarActions={[
          <Button key="pending-reviews" onClick={() => openReviewDialog()}>
            待确认
          </Button>,
        ]}
      />

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

      <Modal
        footer={null}
        onCancel={() => setReviewDialog(undefined)}
        open={Boolean(reviewDialog)}
        title={reviewDialog?.task ? `确认输出：${reviewDialog.task.label}` : '待确认'}
        width={860}
      >
        {reviewsError ? (
          <Alert className="management-list-alert" showIcon title={formatRemoteRowsError(reviewsError)} type="error" />
        ) : null}
        <ProTable<TaskCenterReviewRecord>
          columns={reviewColumns}
          dataSource={visibleReviewRows}
          loading={reviewsStatus === 'loading'}
          options={false}
          pagination={false}
          rowKey="id"
          search={false}
        />
        {visibleReviewRows.length === 0 && reviewsStatus === 'ready' ? (
          <Text type="secondary">当前没有待确认项。</Text>
        ) : null}
      </Modal>

      <Modal
        confirmLoading={requestMoreInfoDialog?.submitting}
        okText="提交补充问题"
        onCancel={() => setRequestMoreInfoDialog(undefined)}
        onOk={() => void handleRequestMoreInfo()}
        open={Boolean(requestMoreInfoDialog)}
        title={
          requestMoreInfoDialog?.review.id
            ? `要求补充信息：${requestMoreInfoDialog.review.id}`
            : '要求补充信息'
        }
        width={640}
      >
        <Form<RequestMoreInfoFormValues> form={requestMoreInfoForm} layout="vertical">
          <Form.Item
            label="补充问题"
            name="questions"
            rules={[{ message: '请输入需要补充的问题', required: true, whitespace: true }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        footer={null}
        onCancel={() => setActionDialog(undefined)}
        open={Boolean(actionDialog)}
        title="任务操作"
        width={640}
      >
        {selectedActionTask ? (
          <div className="task-operation-dialog" data-testid="task-operation-dialog">
            <div className="task-operation-summary" data-testid="task-operation-summary">
              <Text type="secondary">当前任务</Text>
              <Text className="task-operation-title" strong>
                {selectedActionTask.label}
              </Text>
              <Space size={8} wrap>
                <Tag>{taskTypeLabels[selectedActionTask.type] ?? selectedActionTask.type}</Tag>
                <StatusTag
                  color={taskStatusLabels[selectedActionTask.status]?.color ?? 'default'}
                  label={taskStatusLabels[selectedActionTask.status]?.label ?? selectedActionTask.status}
                />
                <Tag>{selectedActionTask.owner}</Tag>
              </Space>
            </div>
            <div
              aria-label="可执行操作"
              className="task-operation-actions"
              data-testid="task-operation-actions"
            >
              {taskActionItems.length ? (
                taskActionItems.map((item) => (
                  <Button block key={item.key} onClick={item.onClick} type={item.type}>
                    {item.label}
                  </Button>
                ))
              ) : (
                <Text type="secondary">当前状态暂无可执行操作。</Text>
              )}
            </div>
          </div>
        ) : null}
      </Modal>

      <Modal
        confirmLoading={submitMoreInfoDialog?.submitting}
        okText="提交补充内容"
        onCancel={() => setSubmitMoreInfoDialog(undefined)}
        onOk={() => void handleSubmitMoreInfo()}
        open={Boolean(submitMoreInfoDialog)}
        title={
          submitMoreInfoDialog?.task.label
            ? `提交补充信息：${submitMoreInfoDialog.task.label}`
            : '提交补充信息'
        }
        width={640}
      >
        <Form<SubmitMoreInfoFormValues> form={submitMoreInfoForm} layout="vertical">
          <Form.Item
            label="补充说明"
            name="answer"
            rules={[{ message: '请输入补充说明', required: true, whitespace: true }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        footer={null}
        onCancel={() => setWritebackDialog(undefined)}
        open={Boolean(writebackDialog)}
        title={
          writebackDialog?.task.label
            ? `模拟 Issue 写回：${writebackDialog.task.label}`
            : '模拟 Issue 写回'
        }
        width={760}
      >
        {writebackDialog?.loading ? <Text type="secondary">写回结果加载中...</Text> : null}
        {writebackDialog?.result ? (
          <Space orientation="vertical" size={12} style={{ width: '100%' }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="状态">
                <StatusTag
                  color={
                    writebackStatusLabels[writebackDialog.result.status]?.color ?? 'default'
                  }
                  label={
                    writebackStatusLabels[writebackDialog.result.status]?.label ??
                    writebackDialog.result.status
                  }
                />
              </Descriptions.Item>
              <Descriptions.Item label="幂等键">
                {writebackDialog.result.idempotencyKey}
              </Descriptions.Item>
            </Descriptions>
            {writebackDialog.result.status === 'not_written' ? (
              <Button
                loading={writebackDialog.submitting}
                onClick={() => void handleCreateWriteback()}
                type="primary"
              >
                生成模拟 Issue
              </Button>
            ) : null}
            <ProTable
              columns={[
                { dataIndex: 'id', title: 'Issue 编号' },
                { dataIndex: 'title', title: '标题' },
                {
                  dataIndex: 'status',
                  title: '状态',
                  render: (_, row) => <StatusTag color="blue" label={String(row.status)} />,
                },
              ]}
              dataSource={writebackDialog.result.issues}
              options={false}
              pagination={false}
              rowKey="id"
              search={false}
            />
            {writebackDialog.result.issues.length === 0 ? (
              <Text type="secondary">当前还没有模拟 Issue。</Text>
            ) : null}
          </Space>
        ) : null}
      </Modal>

      <Modal
        confirmLoading={codeReviewDraft?.submitting}
        okText="生成快照并创建任务"
        onCancel={() => setCodeReviewDraft(undefined)}
        onOk={handleCreateCodeReview}
        open={Boolean(codeReviewDraft)}
        title={
          codeReviewDraft?.task.label
            ? `创建 Code Review：${codeReviewDraft.task.label}`
            : '创建 Code Review'
        }
        width={760}
      >
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          <Form aria-label="创建 Code Review 参数" className="task-code-review-form" layout="vertical">
            <Form.Item label="GitLab 仓库">
              <Select
                disabled={codeReviewDraft?.loading}
                onChange={(repositoryId) =>
                  setCodeReviewDraft((current) =>
                    current ? { ...current, preview: undefined, repositoryId } : current,
                  )
                }
                options={codeReviewDraft?.repositories.map((repository) => ({
                  label: repository.label,
                  value: repository.id,
                }))}
                placeholder="选择 GitLab 仓库"
                style={{ width: '100%' }}
                value={codeReviewDraft?.repositoryId}
              />
            </Form.Item>
            <Form.Item label="MR 编号">
              <InputNumber
                min={1}
                onChange={(mrIid) =>
                  setCodeReviewDraft((current) =>
                    current
                      ? { ...current, mrIid: Number(mrIid ?? 1), preview: undefined }
                      : current,
                  )
                }
                precision={0}
                style={{ width: '100%' }}
                value={codeReviewDraft?.mrIid}
              />
            </Form.Item>
            <Form.Item>
              <Button loading={codeReviewDraft?.loading} onClick={handlePreviewCodeReview}>
                预览 MR
              </Button>
            </Form.Item>
          </Form>
          {codeReviewDraft?.repositories.length === 0 && !codeReviewDraft.loading ? (
            <Text type="secondary">当前产品没有可用 GitLab 仓库。</Text>
          ) : null}
          {codeReviewDraft?.preview ? (
            <Descriptions column={1} size="small">
              <Descriptions.Item label="标题">{codeReviewDraft.preview.title}</Descriptions.Item>
              <Descriptions.Item label="作者">{codeReviewDraft.preview.author}</Descriptions.Item>
              <Descriptions.Item label="分支">
                {codeReviewDraft.preview.sourceBranch ?? '-'} →{' '}
                {codeReviewDraft.preview.targetBranch ?? '-'}
              </Descriptions.Item>
              <Descriptions.Item label="变更文件">
                {codeReviewDraft.preview.changedFileCount}
              </Descriptions.Item>
              <Descriptions.Item label="GitLab 回写">
                {codeReviewDraft.preview.writebackAllowed ? '允许' : '不回写'}
              </Descriptions.Item>
            </Descriptions>
          ) : null}
        </Space>
      </Modal>

      <Modal
        footer={null}
        onCancel={() => setCodeReviewReport(undefined)}
        open={Boolean(codeReviewReport)}
        title={
          codeReviewReport?.task.label
            ? `Code Review 报告：${codeReviewReport.task.label}`
            : 'Code Review 报告'
        }
        width={760}
      >
        {codeReviewReport?.loading ? <Text type="secondary">报告加载中...</Text> : null}
        {codeReviewReport?.report ? (
          <Space orientation="vertical" size={12} style={{ width: '100%' }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="状态">{codeReviewReport.report.status}</Descriptions.Item>
              <Descriptions.Item label="风险等级">
                {codeReviewReport.report.riskLevel}
              </Descriptions.Item>
              <Descriptions.Item label="GitLab 回写">
                {codeReviewReport.report.gitlabWritebackPerformed ? '已回写' : '未回写'}
              </Descriptions.Item>
            </Descriptions>
            <Paragraph>{codeReviewReport.report.summary}</Paragraph>
            <Input.TextArea
              autoSize={{ maxRows: 14, minRows: 6 }}
              readOnly
              value={
                codeReviewReport.report.findings.length
                  ? codeReviewReport.report.findings.map(formatFinding).join('\n\n')
                  : '暂无问题'
              }
            />
          </Space>
        ) : null}
      </Modal>
    </>
  );
}
