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
import type { TableProps } from 'antd';
import { type Key, useCallback, useEffect, useMemo, useState } from 'react';

import { ManagementBatchResultModal, type ManagementBatchResult } from '../../components/ManagementBatchResultModal';
import {
  ManagementListPage,
  StatusTag,
  type ManagementListQuery,
} from '../../components/ManagementListPage';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
  useRemoteRows,
} from '../../hooks/useRemoteRows';
import {
  approveTaskCenterReview,
  batchCancelTaskCenterTasks,
  batchRetryTaskCenterTasks,
  createAutomatedTestingTask,
  createCodeReviewTask,
  createDevelopmentPlanningTask,
  createPostReleaseAnalysisTask,
  createReleaseReadinessTask,
  createTechnicalSolutionTask,
  createTaskWritebackResult,
  editApproveTaskCenterReview,
  fetchCodeReviewReport,
  fetchProductContextOptions,
  fetchProductGitRepositories,
  fetchTaskMarkdown,
  fetchTaskCenterPendingReviewList,
  fetchTaskCenterPendingReviews,
  fetchTaskCenterTaskDetail,
  fetchTaskCenterTasks,
  fetchTaskWritebackResult,
  previewCodeReviewPullRequest,
  rejectTaskCenterReview,
  requestTaskCenterReviewMoreInfo,
  snapshotCodeReviewPullRequest,
  type CodeReviewReportRecord,
  type GitLabMergeRequestSnapshot,
  type GitLabMergeRequestPreview,
  type ProductGitRepositoryOption,
  type RemoteListPerformance,
  type TaskWritebackResultRecord,
  startTaskCenterTask,
  submitTaskCenterMoreInfo,
  type TaskCenterReviewRecord,
  type TaskCenterTaskRecord,
} from '../../services/aiBrain';
import { formatMutationError } from '../../utils/managementCrud';
import {
  TaskDetailModal,
  type TaskDetailDialogState,
} from './components/TaskDetailModal';

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

const taskBatchCancellableStatuses = new Set([
  'draft',
  'running',
  'waiting_more_info',
  'waiting_review',
  'writing_back',
]);

const taskBatchRetryableFailureSteps = new Set([
  'code_review_executor_failed',
  'model_gateway_failed',
]);
const PENDING_REVIEW_TABLE_SCROLL = { x: 1040 } satisfies TableProps<TaskCenterReviewRecord>['scroll'];

const taskTypeLabels: Record<string, string> = {
  automated_testing: '自动化测试',
  code_review: 'Code Review',
  development_planning: '开发计划',
  post_release_analysis: '上线后分析',
  product_detail_design: '产品详细设计',
  release_readiness: '发布评估',
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

type EditApproveFormValues = {
  summary: string;
};

type RejectReviewFormValues = {
  reason: string;
};

type SubmitMoreInfoFormValues = {
  answer: string;
};

type TaskRowsState = {
  error?: RemoteRowsError;
  page: number;
  pageSize: number;
  performance?: RemoteListPerformance;
  rows: TaskCenterTaskRecord[];
  status: 'error' | 'loading' | 'ready';
  total: number;
};

type ReviewRowsState = {
  error?: RemoteRowsError;
  rows: TaskCenterReviewRecord[];
  status: 'error' | 'loading' | 'ready';
};

function normalizeQueryValue(value: unknown) {
  return String(value ?? '').trim();
}

function normalizeQueryDate(value: unknown, boundary: 'end' | 'start') {
  const raw = normalizeQueryValue(
    typeof value === 'object' &&
      value !== null &&
      'format' in value &&
      typeof value.format === 'function'
      ? value.format('YYYY-MM-DD')
      : value,
  );
  if (!raw) {
    return undefined;
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
    return boundary === 'end' ? `${raw}T23:59:59Z` : `${raw}T00:00:00Z`;
  }
  return raw;
}

function normalizeQueryDateRange(value: unknown) {
  if (Array.isArray(value)) {
    return [value[0], value[1]] as const;
  }
  const [start = '', end = ''] = normalizeQueryValue(value).split(',');
  return [start, end] as const;
}

const taskSortFieldMap: Record<string, string> = {
  createdAt: 'created_at',
  label: 'title',
  owner: 'created_by',
  product: 'product_name',
  status: 'status',
  type: 'task_type',
};

function buildTaskCenterQuery(query: ManagementListQuery) {
  const [createdFrom, createdTo] = normalizeQueryDateRange(query.filters.createdAtValue);
  return {
    createdFrom: normalizeQueryDate(createdFrom, 'start'),
    createdTo: normalizeQueryDate(createdTo, 'end'),
    keyword: normalizeQueryValue(query.filters.label) || undefined,
    owner: normalizeQueryValue(query.filters.owner) || undefined,
    page: query.page,
    pageSize: query.pageSize,
    productId: normalizeQueryValue(query.filters.productId) || undefined,
    sortField: query.sortField ? taskSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeQueryValue(query.filters.status) || undefined,
    taskType: normalizeQueryValue(query.filters.type) || undefined,
  };
}

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
  const filePath = item.file_path ?? item.file ?? item.path ?? item.filename;
  const line =
    item.line_start ??
    item.line ??
    item.line_number ??
    item.start_line ??
    item.lineStart;
  const location = [filePath, line ? `:${line}` : undefined].filter(Boolean).join('');
  const summary = item.message ?? item.summary ?? item.suggestion ?? JSON.stringify(item);
  return `${index + 1}. ${[item.severity, location, summary].filter(Boolean).join(' · ')}`;
}

function formatRiskLevel(level?: string) {
  if (level === 'high') {
    return '高';
  }
  if (level === 'medium') {
    return '中';
  }
  if (level === 'low') {
    return '低';
  }
  return level || '-';
}

function formatRiskSummary(preview?: GitLabMergeRequestPreview) {
  const summary = preview?.riskSummary;
  if (!summary) {
    return '-';
  }
  const largestFile = summary.largestFile?.path
    ? `最大文件 ${summary.largestFile.path} (${summary.largestFile.lineCount ?? 0} 行)`
    : '无最大文件';
  return `${formatRiskLevel(summary.riskLevel)}风险 · ${summary.fileCount ?? 0} 文件 · +${
    summary.totalAdditions ?? 0
  }/-${summary.totalDeletions ?? 0} · ${largestFile}`;
}

function formatPermissionDiagnostics(preview?: GitLabMergeRequestPreview) {
  const diagnostics = preview?.permissionDiagnostics;
  if (!diagnostics) {
    return '未返回诊断信息';
  }
  return [
    `Provider: ${diagnostics.provider ?? '-'}`,
    `Base URL: ${diagnostics.baseUrlConfigured ? '已配置' : '未配置'}`,
    `仓库路径: ${diagnostics.repositoryPathConfigured ? '已配置' : '未配置'}`,
    `凭据引用: ${diagnostics.credentialRefConfigured ? '已配置' : '未配置'}`,
    `Token: ${diagnostics.tokenAvailable ? '可用' : '不可用'}`,
    `远端回写: ${diagnostics.writebackAllowed ? '允许' : '只读'}`,
  ].join(' · ');
}

function formatSnapshotDiffSummary(snapshot: GitLabMergeRequestSnapshot) {
  const summary = snapshot.diffChangeSummary;
  if (!summary || !snapshot.previousSnapshot) {
    return '首次快照，无上一快照对比';
  }
  return `新增 ${summary.addedFilesCount ?? 0} 文件，修改 ${
    summary.modifiedFilesCount ?? 0
  } 文件，移除 ${summary.removedFilesCount ?? 0} 文件`;
}

function formatChangedFileSummary(file: unknown, index: number) {
  if (!file || typeof file !== 'object' || Array.isArray(file)) {
    return `${index + 1}. ${String(file ?? '-')}`;
  }
  const item = file as Record<string, unknown>;
  const path = item.path ?? item.file_path ?? item.file ?? item.filename ?? '-';
  return `${index + 1}. ${path} · +${item.additions ?? 0}/-${item.deletions ?? 0}`;
}

export default function TaskCenterPage() {
  const [editApproveForm] = Form.useForm<EditApproveFormValues>();
  const [rejectReviewForm] = Form.useForm<RejectReviewFormValues>();
  const [requestMoreInfoForm] = Form.useForm<RequestMoreInfoFormValues>();
  const [submitMoreInfoForm] = Form.useForm<SubmitMoreInfoFormValues>();
  const [markdownPreview, setMarkdownPreview] = useState<{
    content: string;
    title: string;
  }>();
  const [codeReviewDraft, setCodeReviewDraft] = useState<{
    loading: boolean;
    lastSnapshot?: GitLabMergeRequestSnapshot;
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
  const selectedCodeReviewRepository = useMemo(
    () =>
      codeReviewDraft?.repositories.find(
        (repository) => repository.id === codeReviewDraft.repositoryId,
      ),
    [codeReviewDraft],
  );
  const codeReviewSourceLabel =
    selectedCodeReviewRepository?.provider === 'github' ? 'GitHub PR' : 'GitLab MR';
  const [taskDetailDialog, setTaskDetailDialog] = useState<TaskDetailDialogState>();
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
  const [editApproveDialog, setEditApproveDialog] = useState<{
    review: TaskCenterReviewRecord;
    submitting: boolean;
  }>();
  const [rejectReviewDialog, setRejectReviewDialog] = useState<{
    review: TaskCenterReviewRecord;
    submitting: boolean;
  }>();
  const [submitMoreInfoDialog, setSubmitMoreInfoDialog] = useState<{
    submitting: boolean;
    task: TaskCenterTaskRecord;
  }>();
  const [taskBatchResult, setTaskBatchResult] = useState<ManagementBatchResult | null>(null);
  const [taskQuery, setTaskQuery] = useState<ManagementListQuery>({
    filters: {},
    page: 1,
    pageSize: 10,
    sortField: 'createdAt',
    sortOrder: 'descend',
  });
  const [taskRowsState, setTaskRowsState] = useState<TaskRowsState>({
    page: 1,
    pageSize: 10,
    rows: [],
    status: 'loading',
    total: 0,
  });
  const [selectedTaskRowKeys, setSelectedTaskRowKeys] = useState<Key[]>([]);
  const [taskReviewRowsState, setTaskReviewRowsState] = useState<ReviewRowsState>({
    rows: [],
    status: 'ready',
  });
  const loadPendingReviews = useCallback(
    () =>
      fetchTaskCenterPendingReviews({
        page: 1,
        pageSize: 20,
        sortField: 'created_at',
        sortOrder: 'descend',
      }),
    [],
  );
  const {
    error: productOptionsError,
    rows: productOptions,
  } = useRemoteRows(fetchProductContextOptions);
  const {
    error: reviewsError,
    reload: reloadReviews,
    rows: reviewRows,
    status: reviewsStatus,
  } = useRemoteRows(loadPendingReviews);

  useEffect(() => {
    let isCurrent = true;
    fetchTaskCenterTasks(buildTaskCenterQuery(taskQuery))
      .then((result) => {
        if (isCurrent) {
          setTaskRowsState({
            page: result.page,
            pageSize: result.pageSize,
            performance: result.performance,
            rows: result.rows,
            status: 'ready',
            total: result.total,
          });
        }
      })
      .catch((taskError: unknown) => {
        if (!isCurrent) {
          return;
        }
        const normalizedError = taskError as Error & {
          code?: string;
          traceId?: string;
        };
        setTaskRowsState({
          error: {
            code: normalizedError.code,
            message: normalizedError instanceof Error ? normalizedError.message : '接口请求失败',
            traceId: normalizedError.traceId,
          },
          page: taskQuery.page,
          pageSize: taskQuery.pageSize,
          rows: [],
          status: 'error',
          total: 0,
        });
      });
    return () => {
      isCurrent = false;
    };
  }, [taskQuery]);

  const handleTaskQueryChange = useCallback((query: ManagementListQuery) => {
    setTaskRowsState((current) => ({
      ...current,
      page: query.page,
      pageSize: query.pageSize,
      status: 'loading',
    }));
    setTaskQuery(query);
  }, []);

  const reloadTasks = useCallback(async () => {
    setTaskRowsState((current) => ({
      ...current,
      status: 'loading',
    }));
    try {
      const result = await fetchTaskCenterTasks(buildTaskCenterQuery(taskQuery));
      setTaskRowsState({
        page: result.page,
        pageSize: result.pageSize,
        performance: result.performance,
        rows: result.rows,
        status: 'ready',
        total: result.total,
      });
    } catch (taskError: unknown) {
      const normalizedError = taskError as Error & {
        code?: string;
        traceId?: string;
      };
      setTaskRowsState({
        error: {
          code: normalizedError.code,
          message: normalizedError instanceof Error ? normalizedError.message : '接口请求失败',
          traceId: normalizedError.traceId,
        },
        page: taskQuery.page,
        pageSize: taskQuery.pageSize,
        rows: [],
        status: 'error',
        total: 0,
      });
    }
  }, [taskQuery]);

  const reloadTaskCenter = useCallback(async () => {
    await Promise.all([reloadTasks(), reloadReviews()]);
  }, [reloadReviews, reloadTasks]);

  const loadTaskPendingReviews = useCallback(async (task: TaskCenterTaskRecord) => {
    setTaskReviewRowsState({ rows: [], status: 'loading' });
    try {
      const result = await fetchTaskCenterPendingReviewList({
        aiTaskId: task.id,
        page: 1,
        pageSize: 20,
        sortField: 'created_at',
        sortOrder: 'descend',
      });
      setTaskReviewRowsState({ rows: result.rows, status: 'ready' });
    } catch (reviewError: unknown) {
      setTaskReviewRowsState({
        error: normalizeRemoteRowsError(reviewError),
        rows: [],
        status: 'error',
      });
    }
  }, []);

  const selectedTasks = useMemo(
    () => taskRowsState.rows.filter((row) => selectedTaskRowKeys.includes(row.id)),
    [selectedTaskRowKeys, taskRowsState.rows],
  );

  const selectedBatchCancellableTasks = useMemo(
    () => selectedTasks.filter((row) => taskBatchCancellableStatuses.has(row.status)),
    [selectedTasks],
  );

  const selectedBatchRetryableTasks = useMemo(
    () =>
      selectedTasks.filter(
        (row) =>
          row.status === 'failed' &&
          row.currentStep !== undefined &&
          taskBatchRetryableFailureSteps.has(row.currentStep),
      ),
    [selectedTasks],
  );

  const visibleReviewRows = reviewDialog?.task ? taskReviewRowsState.rows : reviewRows;
  const effectiveReviewsError = reviewDialog?.task ? taskReviewRowsState.error : reviewsError;
  const effectiveReviewsStatus = reviewDialog?.task ? taskReviewRowsState.status : reviewsStatus;
  const productFilterOptions = useMemo(
    () =>
      productOptions.map((product) => ({
        label: product.name ?? product.code ?? product.id,
        value: product.id,
      })),
    [productOptions],
  );
  const selectedActionTask = actionDialog?.task;

  const showTaskBatchResult = useCallback((result: ManagementBatchResult) => {
    setTaskBatchResult(result);
    const skippedText = result.skipped.length ? `，跳过 ${result.skipped.length} 个` : '';
    message.success(`${result.primaryLabel} ${result.primaryCount} 个任务${skippedText}`);
  }, []);

  const openReviewDialog = useCallback((task?: TaskCenterTaskRecord) => {
    setReviewDialog({ task });
    if (task) {
      void loadTaskPendingReviews(task);
      return;
    }
    void reloadReviews();
  }, [loadTaskPendingReviews, reloadReviews]);

  const handleStartTask = useCallback(async (task: TaskCenterTaskRecord) => {
    try {
      await startTaskCenterTask(task.id);
      message.success('任务已启动，已进入人工确认');
      await reloadTaskCenter();
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, [reloadTaskCenter]);

  const handleBatchCancelTasks = useCallback(async () => {
    if (!selectedBatchCancellableTasks.length) {
      message.warning('请选择可取消的任务');
      return;
    }
    try {
      const result = await batchCancelTaskCenterTasks({
        reason: '研发任务批量取消',
        task_ids: selectedBatchCancellableTasks.map((task) => task.id),
      });
      showTaskBatchResult({
        batchId: result.batchId,
        primaryCount: result.updatedCount,
        primaryLabel: '已取消',
        skipped: result.skipped,
        title: '批量取消结果',
      });
      setSelectedTaskRowKeys([]);
      await reloadTaskCenter();
    } catch (batchError) {
      message.error(formatMutationError(batchError));
    }
  }, [reloadTaskCenter, selectedBatchCancellableTasks, showTaskBatchResult]);

  const handleBatchRetryTasks = useCallback(async () => {
    if (!selectedBatchRetryableTasks.length) {
      message.warning('请选择可重试的失败任务');
      return;
    }
    try {
      const result = await batchRetryTaskCenterTasks({
        reason: '研发任务批量重试',
        task_ids: selectedBatchRetryableTasks.map((task) => task.id),
      });
      const failedRetryCount = Math.max(result.retriedCount - result.updatedCount, 0);
      const updatedIds = new Set(result.updated.map((task) => task.id));
      showTaskBatchResult({
        batchId: result.batchId,
        primaryCount: result.retriedCount,
        primaryLabel: '已重试',
        secondary: [
          { label: '成功数', value: result.updatedCount },
          { label: '仍失败数', value: failedRetryCount },
        ],
        sections: [
          {
            items: result.retried
              .filter((task) => !updatedIds.has(task.id))
              .map((task) => ({
                id: task.id,
                lines: [
                  `${task.status} · ${task.current_step ?? '-'} · ${task.error_code ?? '-'} · ${
                    task.error_message ?? '-'
                  }`,
                ],
              })),
            title: '仍失败明细',
          },
        ],
        skipped: result.skipped,
        title: '批量重试结果',
      });
      setSelectedTaskRowKeys([]);
      await reloadTaskCenter();
    } catch (batchError) {
      message.error(formatMutationError(batchError));
    }
  }, [reloadTaskCenter, selectedBatchRetryableTasks, showTaskBatchResult]);

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

  const openEditApproveDialog = useCallback((review: TaskCenterReviewRecord) => {
    editApproveForm.setFieldsValue({ summary: review.contentSummary });
    setEditApproveDialog({ review, submitting: false });
  }, [editApproveForm]);

  const handleEditApproveReview = useCallback(async () => {
    if (!editApproveDialog) {
      return;
    }
    const values = await editApproveForm.validateFields();
    setEditApproveDialog((current) => (current ? { ...current, submitting: true } : current));
    try {
      await editApproveTaskCenterReview(editApproveDialog.review.id, editApproveDialog.review.version, {
        summary: values.summary.trim(),
      });
      message.success('修改后确认已提交，任务已完成');
      setEditApproveDialog(undefined);
      setReviewDialog(undefined);
      await reloadTaskCenter();
    } catch (reviewError) {
      setEditApproveDialog((current) => (current ? { ...current, submitting: false } : current));
      message.error(formatMutationError(reviewError));
    }
  }, [editApproveDialog, editApproveForm, reloadTaskCenter]);

  const openRejectReviewDialog = useCallback((review: TaskCenterReviewRecord) => {
    rejectReviewForm.resetFields();
    setRejectReviewDialog({ review, submitting: false });
  }, [rejectReviewForm]);

  const handleRejectReview = useCallback(async () => {
    if (!rejectReviewDialog) {
      return;
    }
    const values = await rejectReviewForm.validateFields();
    setRejectReviewDialog((current) => (current ? { ...current, submitting: true } : current));
    try {
      await rejectTaskCenterReview(
        rejectReviewDialog.review.id,
        rejectReviewDialog.review.version,
        values.reason.trim(),
      );
      message.success('已拒绝该确认项，任务已标记失败');
      setRejectReviewDialog(undefined);
      setReviewDialog(undefined);
      await reloadTaskCenter();
    } catch (reviewError) {
      setRejectReviewDialog((current) => (current ? { ...current, submitting: false } : current));
      message.error(formatMutationError(reviewError));
    }
  }, [rejectReviewDialog, rejectReviewForm, reloadTaskCenter]);

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

  const handleCreateReleaseReadiness = useCallback(async (task: TaskCenterTaskRecord) => {
    try {
      await createReleaseReadinessTask(task);
      message.success('发布评估任务已创建');
      await reloadTaskCenter();
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, [reloadTaskCenter]);

  const handleCreatePostReleaseAnalysis = useCallback(async (task: TaskCenterTaskRecord) => {
    try {
      await createPostReleaseAnalysisTask(task);
      message.success('上线后分析任务已创建');
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
    const draft = codeReviewDraft;
    if (!draft) {
      message.error('请先选择技术方案任务。');
      return;
    }
    const repository = draft.repositories.find((item) => item.id === draft.repositoryId);
    if (!repository) {
      message.error('请选择代码库。');
      return;
    }
    try {
      const preview = await previewCodeReviewPullRequest(repository, draft.mrIid);
      setCodeReviewDraft((current) => (current ? { ...current, preview } : current));
    } catch (taskError) {
      message.error(formatMutationError(taskError));
    }
  }, [codeReviewDraft]);

  const handleCreateCodeReview = useCallback(async () => {
    const draft = codeReviewDraft;
    if (!draft) {
      message.error('请先选择技术方案任务。');
      return;
    }
    const repository = draft.repositories.find((item) => item.id === draft.repositoryId);
    if (!repository) {
      message.error('请选择代码库。');
      return;
    }
    if (!draft.task.requirementId) {
      message.error('缺少需求编号，无法创建 Code Review 任务。');
      return;
    }
    setCodeReviewDraft((current) => (current ? { ...current, submitting: true } : current));
    try {
      const snapshot = await snapshotCodeReviewPullRequest({
        mrIid: draft.mrIid,
        repository,
        requirementId: draft.task.requirementId,
        technicalSolutionTaskId: draft.task.id,
      });
      await createCodeReviewTask(draft.task, snapshot.id, draft.mrIid);
      message.success('Code Review 任务已创建');
      setCodeReviewDraft(undefined);
      Modal.success({
        content: (
          <Space orientation="vertical" size={4}>
            <Text>快照：{snapshot.snapshotReused ? '复用已有快照' : '已生成新快照'}</Text>
            <Text>对比：{formatSnapshotDiffSummary(snapshot)}</Text>
            {snapshot.previousSnapshot ? (
              <Text type="secondary">
                上一快照：{snapshot.previousSnapshot.id ?? '-'} ·{' '}
                {snapshot.previousSnapshot.createdAt ?? '-'}
              </Text>
            ) : null}
          </Space>
        ),
        title: 'Code Review 快照结果',
      });
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

  const handleOpenTaskDetail = useCallback(async (task: TaskCenterTaskRecord) => {
    setTaskDetailDialog({ loading: true, task });
    try {
      const detail = await fetchTaskCenterTaskDetail(task.id);
      setTaskDetailDialog((current) =>
        current?.task.id === task.id ? { ...current, detail, loading: false } : current,
      );
    } catch (taskError) {
      setTaskDetailDialog((current) =>
        current?.task.id === task.id ? { ...current, loading: false } : current,
      );
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

    actions.push({
      key: 'detail',
      label: '查看详情',
      onClick: closeAndRun(() => handleOpenTaskDetail(selectedActionTask)),
    });

    if (selectedActionTask.status === 'draft') {
      actions.push({
        key: 'start',
        label: '启动任务',
        onClick: closeAndRun(() => handleStartTask(selectedActionTask)),
        type: 'primary',
      });
    }

    if (
      selectedActionTask.status === 'failed' &&
      selectedActionTask.currentStep !== undefined &&
      taskBatchRetryableFailureSteps.has(selectedActionTask.currentStep)
    ) {
      actions.push({
        key: 'retry',
        label: '重试任务',
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
          key: 'create-release-readiness',
          label: '生成发布评估',
          onClick: closeAndRun(() => handleCreateReleaseReadiness(selectedActionTask)),
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

    if (
      selectedActionTask.type === 'release_readiness' &&
      selectedActionTask.status === 'completed'
    ) {
      actions.push({
        key: 'create-post-release-analysis',
        label: '生成上线后分析',
        onClick: closeAndRun(() => handleCreatePostReleaseAnalysis(selectedActionTask)),
        type: 'primary',
      });
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
    handleCreatePostReleaseAnalysis,
    handleCreateReleaseReadiness,
    handleCreateTechnicalSolution,
    handleExportMarkdown,
    handleOpenCodeReview,
    handleOpenCodeReviewReport,
    handleOpenTaskDetail,
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
        sorter: true,
        render: (_value, row) => (
          <span className="task-name">
            <strong>{row.label}</strong>
            <small>{taskTypeLabels[row.type] ?? row.type}</small>
          </span>
        ),
      },
      {
        title: '所属产品',
        dataIndex: 'product',
        key: 'product',
        sorter: true,
      },
      {
        title: '状态',
        dataIndex: 'status',
        key: 'status',
        sorter: true,
        render: (_, row) => {
          const statusLabel = taskStatusLabels[row.status] ?? { color: 'blue', label: row.status };
          return <StatusTag color={statusLabel.color} label={statusLabel.label} />;
        },
      },
      {
        title: '创建时间',
        dataIndex: 'createdAt',
        key: 'createdAt',
        sorter: true,
      },
      {
        title: '负责人',
        dataIndex: 'owner',
        key: 'owner',
        sorter: true,
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
        ellipsis: true,
        title: '确认编号',
        width: 180,
      },
      {
        dataIndex: 'stage',
        ellipsis: true,
        title: '确认阶段',
        width: 160,
      },
      {
        dataIndex: 'contentSummary',
        ellipsis: true,
        title: 'AI 输出摘要',
        width: 300,
      },
      {
        dataIndex: 'status',
        title: '状态',
        render: (_, row) => <Tag color="gold">{row.status}</Tag>,
        width: 120,
      },
      {
        fixed: 'right',
        key: 'actions',
        title: '操作',
        valueType: 'option',
        render: (_, row) => (
          <Space size={4}>
            <Button onClick={() => handleApproveReview(row)} type="link">
              确认通过
            </Button>
            <Button onClick={() => openEditApproveDialog(row)} type="link">
              修改后通过
            </Button>
            <Button danger onClick={() => openRejectReviewDialog(row)} type="link">
              拒绝
            </Button>
            <Button onClick={() => openRequestMoreInfoDialog(row)} type="link">
              要求补充
            </Button>
          </Space>
        ),
        width: 280,
      },
    ],
    [handleApproveReview, openEditApproveDialog, openRejectReviewDialog, openRequestMoreInfoDialog],
  );

  return (
    <>
      <ManagementListPage<TaskCenterTaskRecord>
        breadcrumbGroup="需求交付"
        columns={columns}
        dataSource={taskRowsState.rows}
        viewStorageKey="delivery.rd_tasks"
        filters={[
          { label: '任务', name: 'label', type: 'text' },
          {
            label: '所属产品',
            name: 'productId',
            options: productFilterOptions,
            type: 'select',
          },
          {
            label: '任务类型',
            name: 'type',
            options: [
              { label: '产品详细设计', value: 'product_detail_design' },
              { label: '技术方案', value: 'technical_solution' },
              { label: '开发计划', value: 'development_planning' },
              { label: '自动化测试', value: 'automated_testing' },
              { label: '发布评估', value: 'release_readiness' },
              { label: '上线后分析', value: 'post_release_analysis' },
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
          { label: '时间段', name: 'createdAtValue', type: 'dateRange' },
          { label: '负责人', name: 'owner', type: 'text' },
        ]}
        loading={taskRowsState.status === 'loading'}
        notice={formatRemoteRowsError(taskRowsState.error ?? reviewsError ?? productOptionsError)}
        onReload={() => void reloadTaskCenter()}
        remote={{
          onChange: handleTaskQueryChange,
          page: taskRowsState.page,
          pageSize: taskRowsState.pageSize,
          performance: taskRowsState.performance,
          total: taskRowsState.total,
        }}
        rowKey="id"
        rowSelection={{
          getCheckboxProps: (row) => ({
            disabled:
              !taskBatchCancellableStatuses.has(row.status) &&
              !(
                row.status === 'failed' &&
                row.currentStep !== undefined &&
                taskBatchRetryableFailureSteps.has(row.currentStep)
              ),
          }),
          onChange: (keys) => setSelectedTaskRowKeys(keys),
          selectedRowKeys: selectedTaskRowKeys,
        }}
        tableTitle="任务列表"
        title="研发任务"
        toolbarActions={[
          <Button
            disabled={!selectedBatchRetryableTasks.length}
            key="batch-retry"
            onClick={() => void handleBatchRetryTasks()}
          >
            批量重试
          </Button>,
          <Button
            danger
            disabled={!selectedBatchCancellableTasks.length}
            key="batch-cancel"
            onClick={() => void handleBatchCancelTasks()}
          >
            批量取消
          </Button>,
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
          readOnly
          rows={12}
          value={markdownPreview?.content}
        />
      </Modal>

      <ManagementBatchResultModal
        onClose={() => setTaskBatchResult(null)}
        result={taskBatchResult}
        width={760}
      />

      <Modal
        footer={null}
        onCancel={() => setReviewDialog(undefined)}
        open={Boolean(reviewDialog)}
        title={reviewDialog?.task ? `确认输出：${reviewDialog.task.label}` : '待确认'}
        width={860}
      >
        {effectiveReviewsError ? (
          <Alert
            className="management-list-alert"
            showIcon
            title={formatRemoteRowsError(effectiveReviewsError)}
            type="error"
          />
        ) : null}
        <ProTable<TaskCenterReviewRecord>
          columns={reviewColumns}
          dataSource={visibleReviewRows}
          loading={effectiveReviewsStatus === 'loading'}
          options={false}
          pagination={false}
          rowKey="id"
          search={false}
          scroll={PENDING_REVIEW_TABLE_SCROLL}
          tableLayout="fixed"
        />
        {visibleReviewRows.length === 0 && effectiveReviewsStatus === 'ready' ? (
          <Text type="secondary">当前没有待确认项。</Text>
        ) : null}
      </Modal>

      <Modal
        confirmLoading={editApproveDialog?.submitting}
        okText="修改后通过"
        onCancel={() => setEditApproveDialog(undefined)}
        onOk={() => void handleEditApproveReview()}
        open={Boolean(editApproveDialog)}
        title={
          editApproveDialog?.review.id
            ? `修改后通过：${editApproveDialog.review.id}`
            : '修改后通过'
        }
        width={640}
      >
        <Form<EditApproveFormValues> form={editApproveForm} layout="vertical">
          <Form.Item
            label="修订摘要"
            name="summary"
            rules={[{ message: '请输入修订后的摘要', required: true, whitespace: true }]}
          >
            <Input.TextArea rows={5} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        confirmLoading={rejectReviewDialog?.submitting}
        okText="拒绝"
        okButtonProps={{ danger: true }}
        onCancel={() => setRejectReviewDialog(undefined)}
        onOk={() => void handleRejectReview()}
        open={Boolean(rejectReviewDialog)}
        title={
          rejectReviewDialog?.review.id
            ? `拒绝确认：${rejectReviewDialog.review.id}`
            : '拒绝确认'
        }
        width={640}
      >
        <Form<RejectReviewFormValues> form={rejectReviewForm} layout="vertical">
          <Form.Item
            label="拒绝原因"
            name="reason"
            rules={[{ message: '请输入拒绝原因', required: true, whitespace: true }]}
          >
            <Input.TextArea rows={4} />
          </Form.Item>
        </Form>
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

      <TaskDetailModal
        dialog={taskDetailDialog}
        onClose={() => setTaskDetailDialog(undefined)}
        taskStatusLabels={taskStatusLabels}
        taskTypeLabels={taskTypeLabels}
      />

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
            <Form.Item label="代码库">
              <Select
                disabled={codeReviewDraft?.loading}
                onChange={(repositoryId) =>
                  setCodeReviewDraft((current) =>
                    current ? { ...current, preview: undefined, repositoryId } : current,
                  )
                }
                options={codeReviewDraft?.repositories.map((repository) => ({
                  label: `${repository.provider === 'github' ? 'GitHub' : 'GitLab'} · ${
                    repository.label
                  }`,
                  value: repository.id,
                }))}
                placeholder="选择代码库"
                style={{ width: '100%' }}
                value={codeReviewDraft?.repositoryId}
              />
            </Form.Item>
            <Form.Item label={`${codeReviewSourceLabel} 编号`}>
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
                预览 {codeReviewSourceLabel}
              </Button>
            </Form.Item>
          </Form>
          {codeReviewDraft?.repositories.length === 0 && !codeReviewDraft.loading ? (
            <Text type="secondary">当前产品没有可用代码库。</Text>
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
              <Descriptions.Item label="风险摘要">
                {formatRiskSummary(codeReviewDraft.preview)}
              </Descriptions.Item>
              <Descriptions.Item label="远端回写">
                {codeReviewDraft.preview.writebackAllowed ? '允许' : '不回写'}
              </Descriptions.Item>
              <Descriptions.Item label="权限诊断">
                {formatPermissionDiagnostics(codeReviewDraft.preview)}
              </Descriptions.Item>
            </Descriptions>
          ) : null}
          {codeReviewDraft?.preview?.diffFileTree.length ? (
            <Space orientation="vertical" size={8} style={{ width: '100%' }}>
              <Text strong>变更文件树</Text>
              <Space size={[6, 6]} wrap>
                {codeReviewDraft.preview.diffFileTree.map((item) => (
                  <Tag key={item.path} color="blue">
                    {item.path} · {item.fileCount} 文件 · +{item.additions}/-{item.deletions}
                  </Tag>
                ))}
              </Space>
            </Space>
          ) : null}
          {codeReviewDraft?.preview?.changedFilesSummary.length ? (
            <Space orientation="vertical" size={8} style={{ width: '100%' }}>
              <Text strong>变更文件明细</Text>
              <Input.TextArea
                readOnly
                rows={3}
                value={codeReviewDraft.preview.changedFilesSummary
                  .map(formatChangedFileSummary)
                  .join('\n')}
              />
            </Space>
          ) : null}
          {codeReviewDraft?.preview?.reviewChecklist.length ? (
            <Space orientation="vertical" size={8} style={{ width: '100%' }}>
              <Text strong>Review Checklist</Text>
              <Input.TextArea
                readOnly
                rows={3}
                value={codeReviewDraft.preview.reviewChecklist
                  .map((item, index) => `${index + 1}. ${item}`)
                  .join('\n')}
              />
            </Space>
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
              <Descriptions.Item label="远端回写">
                {codeReviewReport.report.gitlabWritebackPerformed ? '已回写' : '未回写'}
              </Descriptions.Item>
              <Descriptions.Item label="需求全链路">
                <Button
                  disabled={!codeReviewReport.task.requirementId}
                  href={
                    codeReviewReport.task.requirementId
                      ? `/delivery/requirements/${codeReviewReport.task.requirementId}/full-chain`
                      : undefined
                  }
                >
                  查看需求全链路
                </Button>
              </Descriptions.Item>
            </Descriptions>
            <Paragraph>{codeReviewReport.report.summary}</Paragraph>
            <Input.TextArea
              readOnly
              rows={6}
              value={
                codeReviewReport.report.findings.length
                  ? codeReviewReport.report.findings.map(formatFinding).join('\n\n')
                  : '暂无问题'
              }
            />
            {codeReviewReport.report.writebackTemplate ? (
              <Space orientation="vertical" size={6} style={{ width: '100%' }}>
                <Text strong>Review 结论回写模板</Text>
                <Input.TextArea
                  readOnly
                  rows={8}
                  value={codeReviewReport.report.writebackTemplate.body}
                />
              </Space>
            ) : null}
          </Space>
        ) : null}
      </Modal>
    </>
  );
}
