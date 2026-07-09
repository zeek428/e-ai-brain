import {
  AlertOutlined,
  ApiOutlined,
  CheckCircleOutlined,
  DashboardOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  QuestionCircleOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { PageContainer } from '@ant-design/pro-components';
import {
  Alert,
  Button,
  Descriptions,
  Empty,
  Form,
  Input,
  Modal,
  Progress,
  Radio,
  Skeleton,
  Space,
  Statistic,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ReactNode } from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import {
  cancelAiExecutorTask,
  cleanupSystemObjectStorage,
  createSystemAlertRule,
  createSystemAlertSubscription,
  fetchSystemAdminWeeklyReport,
  fetchSystemHealth,
  retryAiExecutorTask,
  timeoutAiExecutorTasks,
  updateSystemAlertIncident,
  updateSystemAlertRule,
  updateSystemAlertSubscription,
  type SystemAlertIncidentUpdatePayload,
  type SystemAlertRuleMutationPayload,
  type SystemHealthAlertRecord,
  type SystemHealthCheckRecord,
  type SystemHealthOperations,
  type SystemHealthReport,
} from '../../services/aiBrain';
import { formatDisplayDateTime } from '../../utils/dateTime';
import { navigateTo } from '../../utils/navigation';
import {
  formatRemoteRowsError,
  normalizeRemoteRowsError,
  type RemoteRowsError,
} from '../../hooks/useRemoteRows';

const { Paragraph, Text, Title } = Typography;
const { TextArea } = Input;

const STATUS_LABELS: Record<string, string> = {
  configured: '已配置',
  degraded: '需关注',
  disabled: '已停用',
  enabled: '已启用',
  error: '异常',
  failed: '失败',
  healthy: '健康',
  info: '提示',
  managed: '托管',
  not_configured: '未配置',
  ok: '正常',
  attention: '需关注',
  acknowledged: '已认领',
  cancelled: '已取消',
  claimed: '已领取',
  closed: '已关闭',
  dead_letter: '死信',
  ignored: '已忽略',
  open: '打开',
  pending: '待投递',
  queued: '排队',
  resolving: '处理中',
  running: '运行中',
  sent: '已发送',
  skipped: '已跳过',
  timed_out: '超时',
  warning: '待完善',
};

const STATUS_COLORS: Record<string, string> = {
  attention: 'gold',
  acknowledged: 'blue',
  configured: 'green',
  closed: 'green',
  degraded: 'orange',
  disabled: 'default',
  enabled: 'green',
  error: 'red',
  failed: 'red',
  healthy: 'green',
  ignored: 'default',
  info: 'blue',
  managed: 'green',
  not_configured: 'default',
  ok: 'green',
  open: 'orange',
  pending: 'gold',
  resolving: 'purple',
  sent: 'green',
  skipped: 'default',
  warning: 'gold',
  cancelled: 'default',
  claimed: 'blue',
  dead_letter: 'red',
  queued: 'gold',
  running: 'blue',
  timed_out: 'orange',
};

const OVERALL_COPY: Record<string, { color: string; icon: ReactNode; title: string }> = {
  degraded: {
    color: 'orange',
    icon: <AlertOutlined aria-hidden="true" />,
    title: '存在需要关注的运行项',
  },
  error: {
    color: 'red',
    icon: <ExclamationCircleOutlined aria-hidden="true" />,
    title: '存在阻断级配置或依赖异常',
  },
  ok: {
    color: 'green',
    icon: <CheckCircleOutlined aria-hidden="true" />,
    title: '系统关键能力状态良好',
  },
  warning: {
    color: 'gold',
    icon: <InfoCircleOutlined aria-hidden="true" />,
    title: '系统可用，但仍有配置待完善',
  },
};

function statusTag(status: string) {
  return <Tag color={STATUS_COLORS[status] ?? 'default'}>{STATUS_LABELS[status] ?? status}</Tag>;
}

function formatMetricValue(value: unknown): string {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  if (typeof value === 'boolean') {
    return value ? '是' : '否';
  }
  if (Array.isArray(value)) {
    return value.length ? value.join('、') : '-';
  }
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }
  return String(value);
}

function metricEntries(metrics?: Record<string, unknown>) {
  return Object.entries(metrics ?? {}).filter(([, value]) => value !== undefined);
}

function groupChecksByCategory(checks: SystemHealthCheckRecord[]) {
  return checks.reduce<Record<string, SystemHealthCheckRecord[]>>((groups, check) => {
    const category = check.category || '未分类';
    groups[category] = [...(groups[category] ?? []), check];
    return groups;
  }, {});
}

function attentionChecks(checks: SystemHealthCheckRecord[]) {
  const attention = new Set(['degraded', 'error', 'failed', 'warning']);
  return checks.filter((check) => attention.has(check.status));
}

function SystemHealthCheckItem({ check }: { check: SystemHealthCheckRecord }) {
  const metrics = metricEntries(check.metrics);
  return (
    <section className="system-health-check">
      <div className="system-health-check-main">
        <div className="system-health-check-title">
          <Space size={8} wrap>
            <strong>{check.title}</strong>
            {statusTag(check.status)}
            <Tag>{check.component}</Tag>
          </Space>
          {check.action_href ? (
            <Button onClick={() => navigateTo(check.action_href as string)} size="small" type="link">
              查看配置
            </Button>
          ) : null}
        </div>
        <Paragraph className="system-health-description">{check.description}</Paragraph>
        {check.last_error ? (
          <Alert
            className="system-health-check-alert"
            showIcon
            title={check.last_error}
            type="warning"
          />
        ) : null}
        <Text type="secondary">{check.fix_suggestion}</Text>
      </div>
      {metrics.length ? (
        <Descriptions
          className="system-health-metrics"
          column={{ lg: 3, md: 2, sm: 1, xs: 1 }}
          items={metrics.slice(0, 6).map(([key, value]) => ({
            key,
            label: key,
            children: formatMetricValue(value),
          }))}
          size="small"
        />
      ) : null}
    </section>
  );
}

function SystemHealthShortcut({
  description,
  icon,
  title,
  to,
}: {
  description: string;
  icon: ReactNode;
  title: string;
  to: string;
}) {
  return (
    <button className="system-health-shortcut" onClick={() => navigateTo(to)} type="button">
      <span className="system-health-shortcut-icon">{icon}</span>
      <span>
        <strong>{title}</strong>
        <Text type="secondary">{description}</Text>
      </span>
    </button>
  );
}

function numericMetric(value: unknown, fallback = 0): number {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }
  return fallback;
}

function percentMetric(value: unknown): number {
  const ratio = numericMetric(value, 0);
  if (ratio <= 1) {
    return Math.round(ratio * 100);
  }
  return Math.round(ratio);
}

function OperationMetric({
  tone,
  title,
  value,
}: {
  tone?: 'danger' | 'success' | 'warning';
  title: string;
  value: ReactNode;
}) {
  return (
    <div className="system-health-ops-metric" data-tone={tone ?? 'default'}>
      <Text type="secondary">{title}</Text>
      <strong>{value}</strong>
    </div>
  );
}

function alertSeverityTag(severity: string) {
  const labelMap: Record<string, string> = {
    high: '高',
    info: '提示',
    low: '低',
    medium: '中',
  };
  const colorMap: Record<string, string> = {
    high: 'red',
    info: 'blue',
    low: 'default',
    medium: 'orange',
  };
  return <Tag color={colorMap[severity] ?? 'default'}>{labelMap[severity] ?? severity}</Tag>;
}

function alertStatusTag(status: string) {
  const labelMap: Record<string, string> = {
    acknowledged: '已认领',
    closed: '已关闭',
    ignored: '已忽略',
    open: '打开',
    resolving: '处理中',
  };
  const colorMap: Record<string, string> = {
    acknowledged: 'blue',
    closed: 'green',
    ignored: 'default',
    open: 'orange',
    resolving: 'purple',
  };
  return <Tag color={colorMap[status] ?? 'default'}>{labelMap[status] ?? status}</Tag>;
}

function alertSubscriptionChannelLabel(channel: string) {
  const labels: Record<string, string> = {
    dingtalk: '钉钉',
    email: '邮件',
    in_app: '站内',
    webhook: 'Webhook',
  };
  return labels[channel] ?? channel;
}

function alertHistoryFieldLabel(field: string) {
  const labels: Record<string, string> = {
    close_reason: '关闭原因',
    owner: '负责人',
    postmortem: '复盘记录',
    status: '处理状态',
    touched: '处理记录',
  };
  return labels[field] ?? field;
}

type AlertIncidentFormValues = {
  close_reason?: string;
  owner?: string;
  postmortem?: string;
  status?: string;
};

type AlertSubscriptionFormValues = {
  channel?: string;
  enabled?: boolean;
  scope?: string;
  severity_min?: string;
  target?: string;
};

type AlertRuleFormValues = {
  component?: string;
  condition_json?: string;
  enabled?: boolean;
  name?: string;
  notification_scope?: string;
  owner?: string;
  severity_min?: string;
  source?: string;
};

function parseJsonObjectInput(value?: string): Record<string, unknown> {
  const trimmed = String(value ?? '').trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('CONDITION_JSON_NOT_OBJECT');
  }
  return parsed as Record<string, unknown>;
}

function SystemHealthOperationsPanel({
  onRefresh,
  operations,
}: {
  onRefresh?: () => Promise<void> | void;
  operations: SystemHealthOperations;
}) {
  const [executorActionLoading, setExecutorActionLoading] = useState<string>();
  const [alertActionLoading, setAlertActionLoading] = useState<string>();
  const [objectCleanupLoading, setObjectCleanupLoading] = useState(false);
  const [weeklyReportLoading, setWeeklyReportLoading] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<SystemHealthAlertRecord>();
  const [subscriptionModalOpen, setSubscriptionModalOpen] = useState(false);
  const [ruleModalOpen, setRuleModalOpen] = useState(false);
  const [alertForm] = Form.useForm<AlertIncidentFormValues>();
  const [subscriptionForm] = Form.useForm<AlertSubscriptionFormValues>();
  const [ruleForm] = Form.useForm<AlertRuleFormValues>();
  const alertCenter = operations.alert_center;
  const aiExecutor = operations.ai_executor_ops;
  const knowledge = operations.knowledge_quality_loop;
  const productScores = operations.product_onboarding_scores;
  const permission = operations.permission_diagnostics;
  const dingtalk = operations.dingtalk_lifecycle;
  const helpAndRetention = operations.help_and_retention;
  const securityAudit = operations.security_audit_governance;
  const products = productScores?.products ?? [];
  const alerts = alertCenter?.alerts ?? [];
  const alertRules = alertCenter?.rules ?? [];
  const alertNotifications = alertCenter?.notifications ?? [];
  const alertSubscriptions = alertCenter?.subscriptions ?? [];
  const alertTrend = alertCenter?.trend ?? [];
  const executorStrategy = aiExecutor?.strategy_config ?? {};
  const executorStrategyMatrix = executorStrategy.strategy_matrix ?? [];
  const executorStrategyIssues = executorStrategy.configuration_issues ?? [];
  const retentionPolicies = helpAndRetention?.retention_policies ?? [];
  const retentionCleanup = helpAndRetention?.cleanup_status ?? {};
  const retentionExpiredRecords = retentionCleanup.expired_records ?? [];
  const objectStorageCleanup = helpAndRetention?.object_storage_cleanup ?? {};
  const screenshots = helpAndRetention?.screenshots?.screenshots ?? [];
  const feedbackLoop = knowledge?.feedback_loop ?? {};
  const activeExecutorTasks = aiExecutor?.latest_active_tasks ?? [];
  const failedExecutorTasks = aiExecutor?.latest_failures ?? [];
  const failureReasons = aiExecutor?.failure_reason_distribution ?? [];
  const scopeComparison = permission?.scope_comparison ?? {};
  const permissionSuggestions = permission?.auto_fix_suggestions ?? [];
  const dingtalkBoundaries = dingtalk?.authorization_boundaries ?? [];
  const dingtalkSubjectSummary = dingtalk?.authorization_subject_summary ?? {};
  const dingtalkSubjects = dingtalk?.authorization_subjects ?? [];
  const qualityGates = knowledge?.quality_gates ?? [];
  const permissionDiagnostics = permission?.diagnostics ?? [];
  const keyExpiryAlerts = dingtalk?.mcp?.key_expiry_alerts ?? [];
  const secretRefIssues = securityAudit?.secret_ref_validation?.issues ?? [];
  const securityGovernanceActions = securityAudit?.governance_actions ?? [];
  const governanceSummary = knowledge?.governance_summary ?? {};
  const governanceCandidates = knowledge?.governance_candidates ?? knowledge?.watch_documents ?? [];

  const showAdminWeeklyReport = async () => {
    setWeeklyReportLoading(true);
    try {
      const report = await fetchSystemAdminWeeklyReport(7);
      Modal.info({
        content: <pre className="system-health-weekly-report-preview">{report.markdown}</pre>,
        title: '管理员周报',
        width: 760,
      });
    } catch (reportError) {
      message.error(formatRemoteRowsError(normalizeRemoteRowsError(reportError)));
    } finally {
      setWeeklyReportLoading(false);
    }
  };

  const reloadAfterExecutorAction = async () => {
    await Promise.resolve(onRefresh?.());
  };

  const reloadAfterAlertAction = async () => {
    await Promise.resolve(onRefresh?.());
  };

  const openAlertIncidentModal = (alert: SystemHealthAlertRecord) => {
    setSelectedAlert(alert);
    alertForm.setFieldsValue({
      close_reason: alert.close_reason ?? '',
      owner: alert.owner ?? '',
      postmortem: alert.postmortem ?? '',
      status: alert.status || 'open',
    });
  };

  const submitAlertIncident = async (values: AlertIncidentFormValues) => {
    if (!selectedAlert) {
      return;
    }
    const payload: SystemAlertIncidentUpdatePayload = {
      close_reason: values.close_reason?.trim() || null,
      owner: values.owner?.trim() || null,
      postmortem: values.postmortem?.trim() || null,
      status: values.status || selectedAlert.status,
    };
    setAlertActionLoading(`alert:${selectedAlert.id}`);
    try {
      await updateSystemAlertIncident(selectedAlert.id, payload);
      message.success('告警处理状态已更新');
      setSelectedAlert(undefined);
      await reloadAfterAlertAction();
    } catch (alertError) {
      message.error(formatRemoteRowsError(normalizeRemoteRowsError(alertError)));
    } finally {
      setAlertActionLoading(undefined);
    }
  };

  const openSubscriptionModal = () => {
    subscriptionForm.setFieldsValue({
      channel: 'email',
      enabled: true,
      scope: 'global',
      severity_min: 'medium',
      target: '',
    });
    setSubscriptionModalOpen(true);
  };

  const submitSubscription = async (values: AlertSubscriptionFormValues) => {
    setAlertActionLoading('subscription:create');
    try {
      await createSystemAlertSubscription({
        channel: values.channel || 'email',
        enabled: values.enabled ?? true,
        scope: values.scope?.trim() || 'global',
        severity_min: values.severity_min || 'medium',
        target: values.target?.trim() || '',
      });
      message.success('告警订阅已保存');
      setSubscriptionModalOpen(false);
      await reloadAfterAlertAction();
    } catch (subscriptionError) {
      message.error(formatRemoteRowsError(normalizeRemoteRowsError(subscriptionError)));
    } finally {
      setAlertActionLoading(undefined);
    }
  };

  const openRuleModal = () => {
    ruleForm.setFieldsValue({
      component: '',
      condition_json: '{}',
      enabled: true,
      name: '',
      notification_scope: 'global',
      owner: '',
      severity_min: 'medium',
      source: 'system_check',
    });
    setRuleModalOpen(true);
  };

  const submitRule = async (values: AlertRuleFormValues) => {
    let conditionJson: Record<string, unknown>;
    try {
      conditionJson = parseJsonObjectInput(values.condition_json);
    } catch {
      message.error('规则条件必须是 JSON 对象，例如 {"status":"warning"}');
      return;
    }
    const payload: SystemAlertRuleMutationPayload = {
      component: values.component?.trim() || null,
      condition_json: conditionJson,
      enabled: values.enabled ?? true,
      name: values.name?.trim() || null,
      notification_scope: values.notification_scope?.trim() || 'global',
      owner: values.owner?.trim() || null,
      severity_min: values.severity_min || 'medium',
      source: values.source?.trim() || 'system_check',
    };
    setAlertActionLoading('rule:create');
    try {
      await createSystemAlertRule(payload);
      message.success('告警规则已保存');
      setRuleModalOpen(false);
      await reloadAfterAlertAction();
    } catch (ruleError) {
      message.error(formatRemoteRowsError(normalizeRemoteRowsError(ruleError)));
    } finally {
      setAlertActionLoading(undefined);
    }
  };

  const toggleAlertRule = async (ruleId: string, enabled: boolean) => {
    setAlertActionLoading(`rule:${ruleId}`);
    try {
      await updateSystemAlertRule(ruleId, { enabled });
      message.success(enabled ? '告警规则已启用' : '告警规则已停用');
      await reloadAfterAlertAction();
    } catch (ruleError) {
      message.error(formatRemoteRowsError(normalizeRemoteRowsError(ruleError)));
    } finally {
      setAlertActionLoading(undefined);
    }
  };

  const toggleAlertSubscription = async (subscriptionId: string, enabled: boolean) => {
    setAlertActionLoading(`subscription:${subscriptionId}`);
    try {
      await updateSystemAlertSubscription(subscriptionId, { enabled });
      message.success(enabled ? '告警订阅已启用' : '告警订阅已停用');
      await reloadAfterAlertAction();
    } catch (subscriptionError) {
      message.error(formatRemoteRowsError(normalizeRemoteRowsError(subscriptionError)));
    } finally {
      setAlertActionLoading(undefined);
    }
  };

  const runExecutorAction = async (
    action: 'cancel' | 'retry' | 'timeout-scan',
    taskId?: string,
  ) => {
    const loadingKey = taskId ? `${action}:${taskId}` : action;
    setExecutorActionLoading(loadingKey);
    try {
      if (action === 'cancel' && taskId) {
        await cancelAiExecutorTask(taskId, '管理员从系统健康运维台取消任务');
        message.success('AI 执行任务已取消');
      } else if (action === 'retry' && taskId) {
        await retryAiExecutorTask(taskId, '管理员从系统健康运维台重试任务');
        message.success('AI 执行任务已重新入队');
      } else {
        const result = await timeoutAiExecutorTasks();
        message.success(result.summary?.message || '超时扫描已完成');
      }
      await reloadAfterExecutorAction();
    } catch (actionError) {
      message.error(formatRemoteRowsError(normalizeRemoteRowsError(actionError)));
    } finally {
      setExecutorActionLoading(undefined);
    }
  };

  const confirmCancelExecutorTask = (taskId: string) => {
    Modal.confirm({
      content: '取消后会保留审计记录，适用于长期排队、卡住或已经不需要执行的任务。',
      okButtonProps: { danger: true },
      okText: '确认取消',
      onOk: () => runExecutorAction('cancel', taskId),
      title: '取消 AI 执行任务',
    });
  };

  const confirmRetryExecutorTask = (taskId: string) => {
    Modal.confirm({
      content: '任务会重新放回队列，建议确认 Runner、插件配置或外部依赖已经恢复。',
      okText: '确认重试',
      onOk: () => runExecutorAction('retry', taskId),
      title: '重试 AI 执行任务',
    });
  };

  const runObjectStorageCleanup = async () => {
    setObjectCleanupLoading(true);
    try {
      const plan = await cleanupSystemObjectStorage({ confirmed: false });
      if (!plan.planned_asset_cleanup_count) {
        message.info('当前没有可同步清理的孤儿知识资产');
        return;
      }
      Modal.confirm({
        content: (
          <div className="system-health-cleanup-confirm">
            <Paragraph>
              将删除 {plan.planned_object_delete_count} 个孤儿对象，并清理 {plan.planned_asset_cleanup_count}
              条知识资产引用。对象删除失败时会保留资产记录并返回错误。
            </Paragraph>
            {plan.blocked_asset_count ? (
              <Text type="secondary">
                另有 {plan.blocked_asset_count} 条资产因信息不完整或仍有关联文档，仅纳入人工复核。
              </Text>
            ) : null}
          </div>
        ),
        okButtonProps: { danger: true },
        okText: '确认同步清理',
        onOk: async () => {
          setObjectCleanupLoading(true);
          try {
            const result = await cleanupSystemObjectStorage({
              confirmed: true,
              reason: '管理员从系统健康页同步清理孤儿知识资产',
            });
            if (result.errors.length) {
              message.warning(`已清理 ${result.cleaned_asset_ids.length} 条资产，${result.errors.length} 个对象删除失败`);
            } else {
              message.success(`已同步清理 ${result.cleaned_asset_ids.length} 条资产引用`);
            }
            await Promise.resolve(onRefresh?.());
          } catch (cleanupError) {
            message.error(formatRemoteRowsError(normalizeRemoteRowsError(cleanupError)));
          } finally {
            setObjectCleanupLoading(false);
          }
        },
        title: '确认对象存储同步清理',
      });
    } catch (cleanupError) {
      message.error(formatRemoteRowsError(normalizeRemoteRowsError(cleanupError)));
    } finally {
      setObjectCleanupLoading(false);
    }
  };

  return (
    <section className="system-health-panel system-health-operations">
      <div className="system-health-section-heading">
        <div>
          <Title level={4}>平台治理运维台</Title>
          <Text type="secondary">从告警、执行、知识、产品、权限、钉钉授权和归档策略看闭环质量</Text>
        </div>
      </div>

      <div className="system-health-ops-grid">
        <article className="system-health-ops-card system-health-ops-card-wide">
          <div className="system-health-ops-card-heading">
            <strong>系统健康告警中心</strong>
            <Space size={4}>
              <Tag color={alertCenter?.summary?.open_count ? 'orange' : 'green'}>
                {alertCenter?.summary?.open_count ?? 0} 个打开
              </Tag>
              <Button size="small" type="link" onClick={openSubscriptionModal}>
                新增订阅
              </Button>
              <Button size="small" type="link" onClick={openRuleModal}>
                新增规则
              </Button>
            </Space>
          </div>
          <div className="system-health-ops-metric-grid">
            <OperationMetric
              title="高优先级"
              tone={alertCenter?.summary?.high_count ? 'danger' : 'success'}
              value={alertCenter?.summary?.high_count ?? 0}
            />
            <OperationMetric title="中优先级" value={alertCenter?.summary?.medium_count ?? 0} />
            <OperationMetric title="低优先级" value={alertCenter?.summary?.low_count ?? 0} />
            <OperationMetric title="处理中" value={alertCenter?.summary?.resolving_count ?? 0} />
            <OperationMetric
              title="待通知"
              tone={numericMetric(alertCenter?.summary?.failed_notification_count) ? 'danger' : 'success'}
              value={formatMetricValue(alertCenter?.summary?.pending_notification_count)}
            />
            <OperationMetric
              title="启用规则"
              value={`${formatMetricValue(alertCenter?.summary?.enabled_rule_count)} / ${formatMetricValue(alertCenter?.summary?.rule_count)}`}
            />
          </div>
          <div className="system-health-ops-list">
            {alerts.slice(0, 5).map((alert) => (
              <div
                className="system-health-alert-row"
                key={alert.id}
              >
                <span>
                  {alertSeverityTag(alert.severity)}
                  {alertStatusTag(alert.status)}
                  <strong>{alert.title}</strong>
                </span>
                <Text type="secondary">
                  {alert.owner || '平台管理员'}
                  {alert.last_seen_at ? ` · ${formatDisplayDateTime(alert.last_seen_at)}` : ''}
                </Text>
                <Space size={4}>
                  {alert.action_href ? (
                    <Button size="small" type="link" onClick={() => navigateTo(alert.action_href as string)}>
                      查看
                    </Button>
                  ) : null}
                  <Button
                    aria-label={`处理告警 ${alert.title}`}
                    loading={alertActionLoading === `alert:${alert.id}`}
                    size="small"
                    type="link"
                    onClick={() => openAlertIncidentModal(alert)}
                  >
                    处理
                  </Button>
                </Space>
              </div>
            ))}
            {!alerts.length ? <Empty description="暂无打开告警" image={Empty.PRESENTED_IMAGE_SIMPLE} /> : null}
          </div>
          {alertRules.length ? (
            <div className="system-health-quality-gates" aria-label="告警规则">
              {alertRules.slice(0, 4).map((rule) => (
                <Button
                  key={rule.id}
                  loading={alertActionLoading === `rule:${rule.id}`}
                  onClick={() => void toggleAlertRule(rule.id, !rule.enabled)}
                  size="small"
                  type={rule.enabled ? 'link' : 'text'}
                >
                  {rule.enabled ? `停用规则 ${rule.name}` : `启用规则 ${rule.name}`} · {rule.severity_min}
                </Button>
              ))}
            </div>
          ) : null}
          <div className="system-health-alert-subscriptions" aria-label="告警订阅">
            {alertSubscriptions.slice(0, 4).map((subscription) => (
              <div className="system-health-alert-subscription-row" key={subscription.id}>
                <span>
                  <Tag color={subscription.enabled ? 'green' : 'default'}>
                    {subscription.enabled ? '启用' : '停用'}
                  </Tag>
                  <Tag>{alertSubscriptionChannelLabel(subscription.channel)}</Tag>
                  <Text ellipsis={{ tooltip: subscription.target }}>{subscription.target}</Text>
                </span>
                <Text type="secondary">
                  {subscription.scope || 'global'} · {subscription.severity_min || 'medium'}+
                </Text>
                <Button
                  loading={alertActionLoading === `subscription:${subscription.id}`}
                  size="small"
                  type="link"
                  onClick={() => void toggleAlertSubscription(subscription.id, !subscription.enabled)}
                >
                  {subscription.enabled ? '停用订阅' : '启用订阅'}
                </Button>
              </div>
            ))}
            {!alertSubscriptions.length ? (
              <Text type="secondary">暂无告警订阅，建议至少配置一个高优先级通知目标。</Text>
            ) : null}
          </div>
          {alertNotifications.length ? (
            <div className="system-health-alert-subscriptions" aria-label="告警通知记录">
              {alertNotifications.slice(0, 4).map((notification) => (
                <div className="system-health-alert-subscription-row" key={notification.id}>
                  <span>
                    {statusTag(notification.status)}
                    <Tag>{alertSubscriptionChannelLabel(notification.channel)}</Tag>
                    <Text ellipsis={{ tooltip: notification.target }}>{notification.target}</Text>
                  </span>
                  <Text type="secondary">
                    {notification.severity} · {notification.created_at ? formatDisplayDateTime(notification.created_at) : '-'}
                  </Text>
                </div>
              ))}
            </div>
          ) : null}
          {alertTrend.length ? (
            <div className="system-health-quality-gates" aria-label="告警历史趋势">
              {alertTrend.slice(-4).map((item) => (
                <Tag key={String(item.date)}>
                  {String(item.date)}：打开 {formatMetricValue(item.opened)} / 关闭 {formatMetricValue(item.closed)}
                </Tag>
              ))}
            </div>
          ) : null}
        </article>

        <article className="system-health-ops-card">
          <div className="system-health-ops-card-heading">
            <strong>AI 任务执行运维台</strong>
            <Space size={4}>
              <Button
                loading={executorActionLoading === 'timeout-scan'}
                size="small"
                type="link"
                onClick={() => void runExecutorAction('timeout-scan')}
              >
                扫超时
              </Button>
              <Button size="small" type="link" onClick={() => navigateTo('/tasks/plugins')}>
                运维
              </Button>
            </Space>
          </div>
          <div className="system-health-ops-metric-grid">
            <OperationMetric title="排队" value={formatMetricValue(aiExecutor?.summary?.queued_count)} />
            <OperationMetric title="运行中" value={formatMetricValue(aiExecutor?.summary?.running_count)} />
            <OperationMetric
              title="失败/死信"
              tone={numericMetric(aiExecutor?.summary?.failed_total) ? 'danger' : 'success'}
              value={formatMetricValue(aiExecutor?.summary?.failed_total)}
            />
            <OperationMetric title="待审批" value={formatMetricValue(aiExecutor?.summary?.pending_approval_count)} />
          </div>
          <Text type="secondary">
            队列压力 {formatMetricValue(percentMetric(aiExecutor?.summary?.queue_pressure))}%；
            Runner {formatMetricValue(aiExecutor?.runner_health?.active_runner_count)} 个可用。
            可取消 {formatMetricValue(aiExecutor?.operation_targets?.cancellable_count)} 个；
            可重试 {formatMetricValue(aiExecutor?.operation_targets?.retryable_count)} 个；
            待扫超时 {formatMetricValue(aiExecutor?.operation_targets?.timeout_scan_count)} 个。
          </Text>
          <div className="system-health-quality-gates" aria-label="AI执行策略配置">
            <Tag color={executorStrategy.status === 'attention' ? 'orange' : 'green'}>
              策略配置 {executorStrategy.status === 'attention' ? '需关注' : '已配置'}
            </Tag>
            {executorStrategyMatrix.slice(0, 4).map((item) => {
              const threshold = item.threshold as Record<string, unknown> | undefined;
              const thresholdText = threshold
                ? `${formatMetricValue(threshold.min)}-${formatMetricValue(threshold.max)}${item.unit === 'seconds' ? 's' : ''}`
                : formatMetricValue(item.source);
              return (
                <Tag color={item.status === 'attention' ? 'orange' : 'blue'} key={String(item.key)}>
                  {String(item.label || item.key)}：{thresholdText}
                </Tag>
              );
            })}
          </div>
          {executorStrategyMatrix.length ? (
            <div className="system-health-executor-strategy-list" aria-label="AI执行策略矩阵">
              {executorStrategyMatrix.slice(0, 3).map((item) => (
                <div key={String(item.key)}>
                  <strong>{String(item.label || item.key)}</strong>
                  <Text type="secondary">{String(item.action || item.source || '-')}</Text>
                </div>
              ))}
            </div>
          ) : null}
          {executorStrategyIssues.length ? (
            <div className="system-health-quality-gates" aria-label="AI执行策略风险">
              {executorStrategyIssues.slice(0, 3).map((item) => (
                <Tag color={item.level === 'warning' ? 'orange' : 'blue'} key={String(item.target)}>
                  {String(item.message || item.target)}
                </Tag>
              ))}
            </div>
          ) : null}
          {failureReasons.length ? (
            <div className="system-health-quality-gates">
              {failureReasons.slice(0, 4).map((item) => (
                <Tag color="red" key={String(item.reason)}>
                  {String(item.reason)}：{formatMetricValue(item.count)}
                </Tag>
              ))}
            </div>
          ) : null}
          <div className="system-health-executor-tasks">
            {activeExecutorTasks.slice(0, 3).map((task) => (
              <div className="system-health-executor-task-row" key={`active:${task.id}`}>
                <span className="system-health-executor-task-main">
                  {statusTag(task.status || 'queued')}
                  <Text ellipsis={{ tooltip: task.id }}>{task.id || '-'}</Text>
                  <Text type="secondary">{task.runner_id || task.executor_type || '未分配 Runner'}</Text>
                </span>
                <Button
                  disabled={!task.id}
                  loading={task.id ? executorActionLoading === `cancel:${task.id}` : false}
                  size="small"
                  onClick={() => task.id && confirmCancelExecutorTask(task.id)}
                >
                  取消
                </Button>
              </div>
            ))}
            {failedExecutorTasks.slice(0, 3).map((task) => (
              <div className="system-health-executor-task-row" key={`failed:${task.id}`}>
                <span className="system-health-executor-task-main">
                  {statusTag(task.status || 'failed')}
                  <Text ellipsis={{ tooltip: task.id }}>{task.id || '-'}</Text>
                  <Text type="secondary">{task.error_code || task.error_message || '失败原因待补充'}</Text>
                </span>
                <Button
                  disabled={!task.id}
                  loading={task.id ? executorActionLoading === `retry:${task.id}` : false}
                  size="small"
                  onClick={() => task.id && confirmRetryExecutorTask(task.id)}
                >
                  重试
                </Button>
              </div>
            ))}
            {!activeExecutorTasks.length && !failedExecutorTasks.length ? (
              <Empty description="暂无需要处理的执行任务" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : null}
          </div>
        </article>

        <article className="system-health-ops-card">
          <div className="system-health-ops-card-heading">
            <strong>知识中心质量闭环</strong>
            <Button size="small" type="link" onClick={() => navigateTo('/assets/knowledge')}>
              治理
            </Button>
          </div>
          <div className="system-health-ops-metric-grid">
            <OperationMetric title="文档" value={formatMetricValue(knowledge?.summary?.total_documents)} />
            <OperationMetric
              title="可检索率"
              tone={percentMetric(knowledge?.summary?.searchable_ratio) >= 80 ? 'success' : 'warning'}
              value={`${percentMetric(knowledge?.summary?.searchable_ratio)}%`}
            />
            <OperationMetric
              title="索引失败"
              tone={numericMetric(knowledge?.summary?.index_failed_documents) ? 'danger' : 'success'}
              value={formatMetricValue(knowledge?.summary?.index_failed_documents)}
            />
            <OperationMetric title="待审核沉淀" value={formatMetricValue(knowledge?.summary?.pending_deposit_count)} />
            <OperationMetric
              title="无结果率"
              tone={numericMetric(feedbackLoop.no_result_rate) > 0.3 ? 'warning' : 'success'}
              value={
                feedbackLoop.no_result_rate === null || feedbackLoop.no_result_rate === undefined
                  ? '-'
                  : `${percentMetric(feedbackLoop.no_result_rate)}%`
              }
            />
          </div>
          <div className="system-health-quality-gates">
            {qualityGates.slice(0, 3).map((gate) => (
              <Tag color={gate.passed ? 'green' : 'orange'} key={String(gate.metric)}>
                {String(gate.metric)}：{gate.passed ? '达标' : '需关注'}
              </Tag>
            ))}
          </div>
          <div className="system-health-knowledge-governance" aria-label="知识治理待办">
            <div className="system-health-knowledge-governance-summary">
              <Tag color={numericMetric(governanceSummary.governance_candidate_count) ? 'orange' : 'green'}>
                治理待办 {formatMetricValue(governanceSummary.governance_candidate_count)}
              </Tag>
              <Tag color={numericMetric(governanceSummary.stale_document_count) ? 'gold' : 'green'}>
                过期文档 {formatMetricValue(governanceSummary.stale_document_count)}
              </Tag>
              <Tag color={numericMetric(governanceSummary.keyword_only_document_count) ? 'blue' : 'green'}>
                仅关键词 {formatMetricValue(governanceSummary.keyword_only_document_count)}
              </Tag>
              <Tag color={numericMetric(governanceSummary.zero_chunk_document_count) ? 'red' : 'green'}>
                无分片 {formatMetricValue(governanceSummary.zero_chunk_document_count)}
              </Tag>
            </div>
            {governanceCandidates.length ? (
              <div className="system-health-knowledge-governance-list">
                {governanceCandidates.slice(0, 4).map((candidate) => {
                  const severity = String(candidate.severity ?? 'low');
                  const severityColor = severity === 'high' ? 'red' : severity === 'medium' ? 'orange' : 'blue';
                  return (
                    <div className="system-health-knowledge-governance-item" key={String(candidate.document_id ?? candidate.title)}>
                      <div className="system-health-knowledge-governance-title">
                        <Text strong ellipsis={{ tooltip: candidate.title }}>
                          {formatMetricValue(candidate.title)}
                        </Text>
                        <Tag color={severityColor}>{severity === 'high' ? '高' : severity === 'medium' ? '中' : '低'}</Tag>
                      </div>
                      <Text type="secondary">
                        {formatMetricValue(candidate.reason)}
                        {candidate.knowledge_space_name ? ` · 空间 ${candidate.knowledge_space_name}` : ''}
                        {candidate.updated_at ? ` · ${formatDisplayDateTime(candidate.updated_at)}` : ''}
                      </Text>
                      <Text type="secondary">{formatMetricValue(candidate.suggested_action)}</Text>
                    </div>
                  );
                })}
              </div>
            ) : (
              <Empty description="暂无知识治理待办" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </div>
          <Text type="secondary">
            引用点击率 {feedbackLoop.citation_click_rate === null || feedbackLoop.citation_click_rate === undefined ? '-' : `${percentMetric(feedbackLoop.citation_click_rate)}%`}
            ，反馈准确率 {feedbackLoop.rag_citation_accuracy_proxy === null || feedbackLoop.rag_citation_accuracy_proxy === undefined ? '-' : `${percentMetric(feedbackLoop.rag_citation_accuracy_proxy)}%`}
          </Text>
        </article>

        <article className="system-health-ops-card system-health-ops-card-wide">
          <div className="system-health-ops-card-heading">
            <strong>产品接入完整度评分</strong>
            <Button size="small" type="link" onClick={() => navigateTo('/assets/products')}>
              接入向导
            </Button>
          </div>
          <div className="system-health-ops-metric-grid">
            <OperationMetric title="平均分" value={formatMetricValue(productScores?.summary?.average_score)} />
            <OperationMetric title="已就绪" tone="success" value={formatMetricValue(productScores?.summary?.ready_count)} />
            <OperationMetric title="部分接入" value={formatMetricValue(productScores?.summary?.partial_count)} />
            <OperationMetric
              title="高风险"
              tone={numericMetric(productScores?.summary?.at_risk_count) ? 'danger' : 'success'}
              value={formatMetricValue(productScores?.summary?.at_risk_count)}
            />
          </div>
          <div className="system-health-product-score-list">
            {products.slice(0, 6).map((product) => (
              <div className="system-health-product-score" key={product.product_id}>
                <div>
                  <strong>{product.name}</strong>
                <Text type="secondary">
                  {product.missing_items?.length ? product.missing_items.join('、') : '接入信息完整'}
                </Text>
                <Text type="secondary">
                  插件 {formatMetricValue(product.plugin_connection_count)}
                  {numericMetric(product.plugin_failed_connection_count) ? ` / 失败 ${formatMetricValue(product.plugin_failed_connection_count)}` : ''}
                  {' · '}
                  权限范围 {formatMetricValue(product.permission_scope_count)}
                  {' · '}
                  可检索文档 {formatMetricValue(product.searchable_knowledge_document_count)}
                </Text>
                <Space size={4} wrap>
                  {statusTag(product.recent_health_status ?? 'attention')}
                  <Text type="secondary">
                    {product.recent_health_check?.summary ?? '健康检查待生成'}
                  </Text>
                </Space>
              </div>
              <Progress percent={product.score} size="small" status={product.score >= 80 ? 'success' : 'normal'} />
            </div>
            ))}
            {!products.length ? <Empty description="暂无活跃产品" image={Empty.PRESENTED_IMAGE_SIMPLE} /> : null}
          </div>
        </article>

        <article className="system-health-ops-card">
          <div className="system-health-ops-card-heading">
            <strong>权限诊断增强</strong>
            <Button size="small" type="link" onClick={() => navigateTo('/system/roles')}>
              权限矩阵
            </Button>
          </div>
          <div className="system-health-ops-metric-grid">
            <OperationMetric title="启用角色" value={formatMetricValue(permission?.summary?.active_role_count)} />
            <OperationMetric
              title="菜单缺口"
              tone={numericMetric(permission?.summary?.roles_with_menu_permission_gaps) ? 'warning' : 'success'}
              value={formatMetricValue(permission?.summary?.roles_with_menu_permission_gaps)}
            />
            <OperationMetric
              title="高风险角色"
              tone={numericMetric(permission?.summary?.roles_with_high_risk_permissions) ? 'danger' : 'success'}
              value={formatMetricValue(permission?.summary?.roles_with_high_risk_permissions)}
            />
          </div>
          {permissionDiagnostics.slice(0, 2).map((item) => (
            <Alert
              className="system-health-ops-inline-alert"
              key={String(item.message)}
              showIcon
              title={String(item.message)}
              type={item.level === 'risk' ? 'warning' : 'info'}
            />
          ))}
          <div className="system-health-quality-gates">
            {Object.entries(scopeComparison).slice(0, 4).map(([roleCode, counts]) => (
              <Tag key={roleCode}>
                {roleCode}：读 {formatMetricValue((counts as Record<string, unknown>).read)} / 写 {formatMetricValue((counts as Record<string, unknown>).write)}
              </Tag>
            ))}
            {permissionSuggestions.slice(0, 1).map((item) => (
              <Tag color="gold" key={String(item.action)}>
                {String(item.action)}
              </Tag>
            ))}
          </div>
        </article>

        <article className="system-health-ops-card">
          <div className="system-health-ops-card-heading">
            <strong>钉钉授权生命周期</strong>
            <Button size="small" type="link" onClick={() => navigateTo('/tasks/plugins')}>
              连接管理
            </Button>
          </div>
          <div className="system-health-ops-metric-grid">
            <OperationMetric title="绑定用户" value={formatMetricValue(dingtalk?.user_bindings?.active_identity_count)} />
            <OperationMetric title="MCP 连接" value={formatMetricValue(dingtalk?.mcp?.connection_count)} />
            <OperationMetric
              title="测试失败"
              tone={numericMetric(dingtalk?.mcp?.failed_connection_count) ? 'danger' : 'success'}
              value={formatMetricValue(dingtalk?.mcp?.failed_connection_count)}
            />
            <OperationMetric title="即将到期" value={formatMetricValue(dingtalk?.mcp?.soon_expiring_count)} />
          </div>
          <div className="system-health-dingtalk-subject-summary" aria-label="钉钉授权主体统计">
            <Tag color="blue">个人 {formatMetricValue(dingtalkSubjectSummary.user)}</Tag>
            <Tag color="purple">系统 {formatMetricValue(dingtalkSubjectSummary.system)}</Tag>
            <Tag color="cyan">应用 {formatMetricValue(dingtalkSubjectSummary.app)}</Tag>
            {numericMetric(dingtalkSubjectSummary.unknown) ? (
              <Tag color="gold">未声明 {formatMetricValue(dingtalkSubjectSummary.unknown)}</Tag>
            ) : null}
          </div>
          {dingtalkBoundaries.length ? (
            <div className="system-health-dingtalk-boundaries" aria-label="钉钉授权边界说明">
              {dingtalkBoundaries.slice(0, 3).map((item) => (
                <div key={String(item.subject_type || item.title)}>
                  <Text strong>{String(item.title || item.subject_type || '授权边界')}</Text>
                  <Text type="secondary">{String(item.description || '-')}</Text>
                </div>
              ))}
            </div>
          ) : null}
          <div className="system-health-dingtalk-subjects" aria-label="钉钉授权主体清单">
            {dingtalkSubjects.slice(0, 4).map((item) => (
              <div key={String(item.connection_id)}>
                <div className="system-health-dingtalk-subject-title">
                  <Text strong>{String(item.subject_label || item.connection_name || item.connection_id || '钉钉连接')}</Text>
                  {statusTag(String(item.expiry_status || item.status || 'unknown'))}
                </div>
                <Text type="secondary">
                  企业 {String(item.corp_name || item.corp_id || '未声明')}
                  {' · '}
                  到期 {item.expires_at ? formatDisplayDateTime(String(item.expires_at)) : '未配置'}
                  {item.days_left !== undefined && item.days_left !== null
                    ? ` · 剩余 ${formatMetricValue(item.days_left)} 天`
                    : ''}
                  {' · '}
                  测试 {String(item.last_test_status || item.status || '未知')}
                </Text>
                <Text type="secondary">{String(item.boundary || '未声明授权主体，建议补齐个人/系统/应用边界。')}</Text>
              </div>
            ))}
            {!dingtalkSubjects.length ? (
              <Text type="secondary">暂无钉钉 MCP 授权主体，新增连接时应声明个人、系统或应用授权。</Text>
            ) : null}
          </div>
          <div className="system-health-quality-gates">
            {keyExpiryAlerts.slice(0, 3).map((item) => (
              <Tag color={item.severity === 'expired' ? 'red' : 'gold'} key={String(item.connection_id)}>
                {String(item.connection_name || '钉钉连接')}：{formatMetricValue(item.days_left)} 天
              </Tag>
            ))}
            {dingtalkSubjects.slice(0, 3).map((item) => (
              <Tag color="blue" key={String(item.connection_id)}>
                {String(item.connection_name || item.connection_id)}：{String(item.subject_type || 'unknown')}
              </Tag>
            ))}
          </div>
        </article>

        <article className="system-health-ops-card">
          <div className="system-health-ops-card-heading">
            <strong>安全审计治理</strong>
            <Space size={4}>
              <Button
                loading={weeklyReportLoading}
                size="small"
                type="link"
                onClick={() => void showAdminWeeklyReport()}
              >
                周报
              </Button>
              <Button size="small" type="link" onClick={() => navigateTo('/governance/audit')}>
                审计
              </Button>
            </Space>
          </div>
          <div className="system-health-ops-metric-grid">
            <OperationMetric
              title="审计周报"
              tone={securityAudit?.admin_weekly_report?.available ? 'success' : 'warning'}
              value={securityAudit?.admin_weekly_report?.available ? '可生成' : '待接入'}
            />
            <OperationMetric
              title="敏感变更"
              value={formatMetricValue(securityAudit?.admin_weekly_report?.sensitive_config_change_count)}
            />
            <OperationMetric
              title="密钥引用"
              tone={numericMetric(securityAudit?.secret_ref_validation?.invalid_ref_count) ? 'warning' : 'success'}
              value={`${formatMetricValue(securityAudit?.secret_ref_validation?.ref_count)} / 异常 ${formatMetricValue(securityAudit?.secret_ref_validation?.invalid_ref_count)}`}
            />
            <OperationMetric
              title="直接密钥"
              value={formatMetricValue(securityAudit?.secret_ref_validation?.direct_secret_count)}
            />
          </div>
          <div className="system-health-quality-gates">
            <Tag color={securityAudit?.sensitive_config_approval?.required ? 'gold' : 'default'}>
              敏感配置审批
            </Tag>
            <Tag color={securityAudit?.high_risk_confirmation?.required ? 'gold' : 'default'}>
              高危二次确认
            </Tag>
            <Tag color={securityAudit?.audit_export?.supported ? 'green' : 'orange'}>
              审计导出
            </Tag>
            {secretRefIssues.slice(0, 2).map((item) => (
              <Tag color="orange" key={String(item.path)}>
                {String(item.path || '密钥引用')}：{String(item.status || '异常')}
              </Tag>
            ))}
          </div>
          {securityGovernanceActions.length ? (
            <div className="system-health-retention-list" aria-label="安全审计治理动作">
              {securityGovernanceActions.slice(0, 6).map((item) => (
                <div key={String(item.key || item.title)}>
                  <strong>
                    {alertSeverityTag(String(item.severity || 'low'))}
                    {String(item.title || '治理动作')}
                  </strong>
                  <Text type="secondary">{String(item.detail || item.target || '-')}</Text>
                </div>
              ))}
            </div>
          ) : null}
          <Text type="secondary">
            近 7 天审计 {formatMetricValue(securityAudit?.admin_weekly_report?.total_audit_events)}
            条，高风险操作 {formatMetricValue(securityAudit?.admin_weekly_report?.high_risk_operation_count)} 条。
          </Text>
        </article>

        <article className="system-health-ops-card system-health-ops-card-wide">
          <div className="system-health-ops-card-heading">
            <strong>帮助截图自动化与数据归档策略</strong>
            <Button size="small" type="link" onClick={() => navigateTo('/help?article=system-admin')}>
              帮助文档
            </Button>
          </div>
          <div className="system-health-ops-metric-grid">
            <OperationMetric
              title="截图覆盖"
              value={`${formatMetricValue(helpAndRetention?.screenshots?.coverage?.ready_count)} / ${formatMetricValue(helpAndRetention?.screenshots?.coverage?.expected_count)}`}
            />
            <OperationMetric
              title="已配置策略"
              value={retentionPolicies.filter((item) => item.configured).length}
            />
            <OperationMetric
              title="过期候选"
              tone={numericMetric(retentionCleanup.total_expired_count) ? 'warning' : 'success'}
              value={formatMetricValue(retentionCleanup.total_expired_count)}
            />
            <OperationMetric
              title="对象清理风险"
              tone={
                numericMetric(objectStorageCleanup.orphan_asset_count)
                || numericMetric(objectStorageCleanup.incomplete_asset_count)
                || numericMetric(objectStorageCleanup.cleanup_failed_count)
                  ? 'warning'
                  : 'success'
              }
              value={`${formatMetricValue(objectStorageCleanup.orphan_asset_count)} / 异常 ${formatMetricValue(objectStorageCleanup.cleanup_failed_count)}`}
            />
          </div>
          <div className="system-health-retention-list">
            {retentionPolicies.slice(0, 6).map((item) => (
              <div key={item.key}>
                <strong>{item.title}</strong>
                <Text type="secondary">{item.days} 天 · {item.configured ? item.env : `${item.env} 默认值`}</Text>
              </div>
            ))}
          </div>
          <div className="system-health-retention-list" aria-label="数据归档清理体检">
            {retentionExpiredRecords.slice(0, 4).map((item) => (
              <div key={`${String(item.policy_key)}:${String(item.id)}`}>
                <strong>{String(item.title || item.id || '过期数据')}</strong>
                <Text type="secondary">
                  {String(item.policy_key || 'retention')} · 超期 {formatMetricValue(item.age_days)} 天
                  {item.status ? ` · ${String(item.status)}` : ''}
                </Text>
              </div>
            ))}
            {!retentionExpiredRecords.length ? (
              <div>
                <strong>暂无过期归档候选</strong>
                <Text type="secondary">{String(retentionCleanup.recommendation || '继续按当前策略观察。')}</Text>
              </div>
            ) : null}
            <div>
              <Space size={8}>
                <strong>对象存储同步清理</strong>
                <Button
                  disabled={!numericMetric(objectStorageCleanup.orphan_asset_count)}
                  loading={objectCleanupLoading}
                  size="small"
                  onClick={() => void runObjectStorageCleanup()}
                >
                  预检并清理
                </Button>
              </Space>
              <Text type="secondary">
                跟踪对象 {formatMetricValue(objectStorageCleanup.tracked_asset_count)}
                {' · '}
                孤儿引用 {formatMetricValue(objectStorageCleanup.orphan_asset_count)}
                {' · '}
                信息不完整 {formatMetricValue(objectStorageCleanup.incomplete_asset_count)}
              </Text>
              <Text type="secondary">
                可删除对象 {formatMetricValue(objectStorageCleanup.cleanup_ready_count)}
                {' · '}
                仅清理引用 {formatMetricValue(objectStorageCleanup.metadata_only_cleanup_count)}
                {' · '}
                阻断复核 {formatMetricValue(objectStorageCleanup.blocked_asset_count)}
              </Text>
            </div>
          </div>
          <div className="system-health-quality-gates">
            {screenshots.map((item) => (
              <Tag color={item.exists ? 'green' : 'orange'} key={String(item.route)}>
                {String(item.article)}截图
              </Tag>
            ))}
          </div>
        </article>
      </div>
      <Modal
        confirmLoading={Boolean(selectedAlert && alertActionLoading === `alert:${selectedAlert.id}`)}
        destroyOnHidden
        okText="保存处理"
        onCancel={() => setSelectedAlert(undefined)}
        onOk={() => alertForm.submit()}
        open={Boolean(selectedAlert)}
        title="处理告警"
        width={680}
      >
        <Form form={alertForm} layout="vertical" onFinish={(values) => void submitAlertIncident(values)}>
          <Descriptions column={1} size="small">
            <Descriptions.Item label="告警">{selectedAlert?.title ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="说明">{selectedAlert?.message ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="首次出现">
              {selectedAlert?.first_seen_at ? formatDisplayDateTime(selectedAlert.first_seen_at) : '-'}
            </Descriptions.Item>
          </Descriptions>
          {selectedAlert?.status_history?.length ? (
            <div className="system-health-alert-history" aria-label="告警处理历史">
              <Text strong>最近处理记录</Text>
              {selectedAlert.status_history.slice(-4).reverse().map((item, index) => (
                <div key={`${item.at ?? 'unknown'}:${index}`}>
                  <span>
                    {formatDisplayDateTime(item.at || '')}
                    {' · '}
                    {STATUS_LABELS[item.from_status || ''] ?? item.from_status ?? '-'}
                    {' -> '}
                    {STATUS_LABELS[item.to_status || ''] ?? item.to_status ?? '-'}
                  </span>
                  <Text type="secondary">
                    {item.owner ? `负责人 ${item.owner}` : '未指定负责人'}
                    {item.changed_fields?.length
                      ? ` · ${item.changed_fields.map(alertHistoryFieldLabel).join('、')}`
                      : ''}
                    {item.close_reason ? ` · ${item.close_reason}` : ''}
                    {item.postmortem_configured ? ' · 已记录复盘' : ''}
                  </Text>
                </div>
              ))}
            </div>
          ) : null}
          <Form.Item label="处理状态" name="status">
            <Radio.Group>
              <Radio.Button value="open">打开</Radio.Button>
              <Radio.Button value="acknowledged">已认领</Radio.Button>
              <Radio.Button value="resolving">处理中</Radio.Button>
              <Radio.Button value="closed">关闭</Radio.Button>
              <Radio.Button value="ignored">忽略</Radio.Button>
            </Radio.Group>
          </Form.Item>
          <Form.Item label="负责人" name="owner">
            <Input placeholder="例如：平台运维 / lzk" />
          </Form.Item>
          <Form.Item label="关闭原因" name="close_reason">
            <TextArea placeholder="关闭或忽略时填写原因，便于后续审计和复盘" rows={3} />
          </Form.Item>
          <Form.Item label="复盘记录" name="postmortem">
            <TextArea placeholder="记录根因、影响范围、处理动作和预防措施" rows={4} />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        confirmLoading={alertActionLoading === 'subscription:create'}
        destroyOnHidden
        okText="保存订阅"
        onCancel={() => setSubscriptionModalOpen(false)}
        onOk={() => subscriptionForm.submit()}
        open={subscriptionModalOpen}
        title="新增告警订阅"
        width={640}
      >
        <Form form={subscriptionForm} layout="vertical" onFinish={(values) => void submitSubscription(values)}>
          <Form.Item label="通知渠道" name="channel">
            <Radio.Group>
              <Radio.Button value="email">邮件</Radio.Button>
              <Radio.Button value="dingtalk">钉钉</Radio.Button>
              <Radio.Button value="webhook">Webhook</Radio.Button>
              <Radio.Button value="in_app">站内</Radio.Button>
            </Radio.Group>
          </Form.Item>
          <Form.Item
            label="通知目标"
            name="target"
            rules={[{ message: '请填写通知目标', required: true }]}
          >
            <Input placeholder="邮箱、钉钉机器人地址、Webhook URL 或用户组" />
          </Form.Item>
          <Form.Item label="最低级别" name="severity_min">
            <Radio.Group>
              <Radio.Button value="low">低</Radio.Button>
              <Radio.Button value="medium">中</Radio.Button>
              <Radio.Button value="high">高</Radio.Button>
            </Radio.Group>
          </Form.Item>
          <Form.Item label="订阅范围" name="scope">
            <Input placeholder="global / system_check / dingtalk_mcp" />
          </Form.Item>
          <Form.Item label="启用订阅" name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        confirmLoading={alertActionLoading === 'rule:create'}
        destroyOnHidden
        okText="保存规则"
        onCancel={() => setRuleModalOpen(false)}
        onOk={() => ruleForm.submit()}
        open={ruleModalOpen}
        title="新增告警规则"
        width={700}
      >
        <Form form={ruleForm} layout="vertical" onFinish={(values) => void submitRule(values)}>
          <Form.Item label="规则名称" name="name" rules={[{ message: '请填写规则名称', required: true }]}>
            <Input placeholder="例如：钉钉授权即将过期" />
          </Form.Item>
          <Form.Item label="来源" name="source">
            <Input placeholder="system_check / dingtalk_lifecycle / product_onboarding" />
          </Form.Item>
          <Form.Item label="组件" name="component">
            <Input placeholder="例如：dingtalk_mcp / smtp / product_score" />
          </Form.Item>
          <Form.Item label="最低级别" name="severity_min">
            <Radio.Group>
              <Radio.Button value="low">低</Radio.Button>
              <Radio.Button value="medium">中</Radio.Button>
              <Radio.Button value="high">高</Radio.Button>
            </Radio.Group>
          </Form.Item>
          <Form.Item label="负责人" name="owner">
            <Input placeholder="规则默认负责人" />
          </Form.Item>
          <Form.Item label="通知范围" name="notification_scope">
            <Input placeholder="global / system / product" />
          </Form.Item>
          <Form.Item label="条件 JSON" name="condition_json">
            <TextArea placeholder='例如 {"status":"warning"}' rows={4} />
          </Form.Item>
          <Form.Item label="启用规则" name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </section>
  );
}

export default function SystemHealthPage() {
  const [report, setReport] = useState<SystemHealthReport>();
  const [error, setError] = useState<RemoteRowsError>();
  const [loading, setLoading] = useState(true);

  const loadHealth = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const loaded = await fetchSystemHealth();
      setReport(loaded);
    } catch (loadError) {
      const normalized = normalizeRemoteRowsError(loadError);
      setError(normalized);
      message.error(normalized.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadHealth();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadHealth]);

  const groupedChecks = useMemo(
    () => groupChecksByCategory(report?.checks ?? []),
    [report?.checks],
  );
  const focusChecks = useMemo(
    () => attentionChecks(report?.checks ?? []),
    [report?.checks],
  );
  const overall = OVERALL_COPY[report?.overall_status ?? 'ok'] ?? OVERALL_COPY.warning;

  return (
    <PageContainer
      breadcrumb={{ items: [{ title: '系统管理' }, { title: '系统健康' }] }}
      extra={[
        <Button
          icon={<QuestionCircleOutlined aria-hidden="true" />}
          key="help"
          onClick={() => navigateTo('/help?article=system-health')}
        >
          查看本页帮助
        </Button>,
        <Button
          icon={<ReloadOutlined aria-hidden="true" />}
          key="reload"
          loading={loading}
          onClick={() => void loadHealth()}
        >
          刷新
        </Button>,
      ]}
      title={false}
    >
      <main className="system-health-page">
        {error ? (
          <Alert
            className="management-list-alert"
            showIcon
            title={formatRemoteRowsError(error)}
            type="warning"
          />
        ) : null}

        {loading && !report ? (
          <section className="system-health-panel">
            <Skeleton active paragraph={{ rows: 8 }} />
          </section>
        ) : report ? (
          <>
            <section className="system-health-hero" data-status={report.overall_status}>
              <div className="system-health-hero-copy">
                <Space align="center" size={12}>
                  <span className="system-health-overall-icon">{overall.icon}</span>
                  <Title level={3}>{overall.title}</Title>
                </Space>
                <Paragraph>
                  统一检查平台依赖、核心配置、运行失败和治理闭环。最近检查时间：
                  {formatDisplayDateTime(report.checked_at)}，Trace ID：{report.trace_id}
                </Paragraph>
              </div>
              <div className="system-health-summary-grid">
                <Statistic title="检查项" value={report.summary.total} />
                <Statistic title="正常" value={report.summary.ok_count} styles={{ content: { color: '#389e0d' } }} />
                <Statistic
                  title="需关注"
                  value={report.summary.needs_attention_count}
                  styles={{ content: { color: report.summary.needs_attention_count ? '#d48806' : '#389e0d' } }}
                />
                <Statistic
                  title="阻断异常"
                  value={report.summary.critical_count}
                  styles={{ content: { color: report.summary.critical_count ? '#cf1322' : '#389e0d' } }}
                />
              </div>
            </section>

            <section className="system-health-shortcuts" aria-label="运维快捷入口">
              <SystemHealthShortcut
                description="查看 API、AI 任务、插件和作业链路"
                icon={<DashboardOutlined aria-hidden="true" />}
                title="执行诊断"
                to="/governance/execution-traces"
              />
              <SystemHealthShortcut
                description="按用户、菜单和权限点定位 Forbidden"
                icon={<SafetyCertificateOutlined aria-hidden="true" />}
                title="权限诊断"
                to="/system/roles"
              />
              <SystemHealthShortcut
                description="检查默认模型、embedding 和调用失败"
                icon={<ApiOutlined aria-hidden="true" />}
                title="模型网关"
                to="/system/model-gateway"
              />
              <SystemHealthShortcut
                description="维护钉钉 MCP、Runner 和插件连接"
                icon={<ToolOutlined aria-hidden="true" />}
                title="插件运维"
                to="/tasks/plugins"
              />
            </section>

            {report.operations ? (
              <SystemHealthOperationsPanel onRefresh={loadHealth} operations={report.operations} />
            ) : null}

            <section className="system-health-panel">
              <div className="system-health-section-heading">
                <Title level={4}>优先处理</Title>
                <Text type="secondary">按异常和风险程度聚合最需要处理的配置或运行问题</Text>
              </div>
              {focusChecks.length ? (
                <div className="system-health-recommendations">
                  {report.recommendations.map((item) => (
                    <div className="system-health-recommendation" key={`${item.component}:${item.title}`}>
                      <div>
                        <Space size={8} wrap>
                          <Tag color={item.severity === 'high' ? 'red' : 'gold'}>
                            {item.severity === 'high' ? '高优先级' : '中优先级'}
                          </Tag>
                          <strong>{item.title}</strong>
                        </Space>
                        <Paragraph>{item.message}</Paragraph>
                      </div>
                      {item.action_href ? (
                        <Button
                          onClick={() => navigateTo(item.action_href as string)}
                          size="small"
                          type="link"
                        >
                          处理
                        </Button>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : (
                <Empty description="暂无需要优先处理的系统健康问题" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </section>

            {Object.entries(groupedChecks).map(([category, checks]) => (
              <section className="system-health-panel" key={category}>
                <div className="system-health-section-heading">
                  <Title level={4}>{category}</Title>
                  <Space wrap>{checks.map((check) => statusTag(check.status))}</Space>
                </div>
                <div className="system-health-check-list">
                  {checks.map((check) => (
                    <SystemHealthCheckItem check={check} key={check.key} />
                  ))}
                </div>
              </section>
            ))}
          </>
        ) : null}
      </main>
    </PageContainer>
  );
}
