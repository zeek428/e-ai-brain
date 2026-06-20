import { BarChartOutlined } from '@ant-design/icons';
import { Button, Segmented, Space, Spin, Tag, Typography } from 'antd';

import {
  type AssistantDraftTemplate,
  type AssistantMetricDetails,
  type AssistantMetrics,
} from '../../../services/aiBrain';

const { Text } = Typography;

const assistantDraftActionLabels: Record<string, string> = {
  create_ai_agent: '创建AI角色',
  create_ai_skill: '创建AI Skill',
  create_analysis_draft: '创建分析草案',
  create_plugin_action: '创建插件动作',
  create_plugin_connection: '创建插件连接',
  create_rd_task: '创建研发任务',
  create_scheduled_job: '创建定时作业',
};

function assistantDraftActionLabel(action?: string) {
  if (!action) {
    return '未知草案';
  }
  return assistantDraftActionLabels[action] ?? action;
}

function metricCount(value?: number) {
  return Number.isFinite(value) ? new Intl.NumberFormat('zh-CN').format(Number(value)) : '-';
}

function metricPercent(value?: number) {
  if (!Number.isFinite(value)) {
    return '-';
  }
  const percentage = Number(value) * 100;
  const rounded = Math.round(percentage * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded.toFixed(0) : rounded.toFixed(1)}%`;
}

function metricRatio(numerator?: number, denominator?: number) {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || Number(denominator) <= 0) {
    return '-';
  }
  return metricPercent(Number(numerator) / Number(denominator));
}

function metricDurationMs(value?: number | null) {
  if (!Number.isFinite(value)) {
    return '-';
  }
  const durationMs = Number(value);
  if (durationMs >= 1000) {
    const seconds = Math.round((durationMs / 1000) * 10) / 10;
    return `${Number.isInteger(seconds) ? seconds.toFixed(0) : seconds.toFixed(1)} 秒`;
  }
  return `${metricCount(durationMs)} ms`;
}

export function AssistantDraftTemplateMarket({
  isLoading,
  onUseTemplate,
  templates,
}: {
  isLoading: boolean;
  onUseTemplate: (template: AssistantDraftTemplate) => void;
  templates: AssistantDraftTemplate[];
}) {
  return (
    <div className="assistant-template-market-panel">
      <div className="assistant-template-market-header">
        <Text strong>模板市场</Text>
        {isLoading ? <Spin size="small" /> : <Tag color="blue">{templates.length}</Tag>}
      </div>
      <div className="assistant-template-market-list">
        {templates.map((template) => (
          <div className="assistant-template-card" key={template.code}>
            <div className="assistant-template-card-title">
              <Text strong>{template.name}</Text>
              <Tag color="green">可生成草案</Tag>
            </div>
            <Text className="assistant-template-description" type="secondary">
              {template.description}
            </Text>
            <Space size={[4, 4]} wrap>
              {template.source_module ? <Tag color="blue">{template.source_module}</Tag> : null}
              {template.draft_action ? <Tag color="default">{template.draft_action}</Tag> : null}
              {template.template_version ? <Tag color="default">{template.template_version}</Tag> : null}
            </Space>
            {template.dependencies?.length ? (
              <Text className="assistant-template-meta" type="secondary">
                依赖：{template.dependencies.join('、')}
              </Text>
            ) : null}
            {template.wizard_steps?.length ? (
              <Text className="assistant-template-meta" type="secondary">
                流程：{template.wizard_steps.join(' -> ')}
              </Text>
            ) : null}
            <Button
              aria-label={`使用模板 ${template.name}`}
              size="small"
              onClick={() => onUseTemplate(template)}
            >
              使用模板
            </Button>
          </div>
        ))}
        {!isLoading && !templates.length ? (
          <Text type="secondary">暂无可用模板</Text>
        ) : null}
      </div>
    </div>
  );
}

export function AssistantMetricsPanel({
  isDetailLoading,
  isLoading,
  metricDetails,
  metrics,
  onChangeWindow,
  onOpenDetail,
  onRefresh,
  windowDays,
}: {
  isDetailLoading?: boolean;
  isLoading: boolean;
  metricDetails?: AssistantMetricDetails;
  metrics?: AssistantMetrics;
  onChangeWindow: (windowDays?: number) => void;
  onOpenDetail: (metric: string) => void;
  onRefresh: () => void;
  windowDays?: number;
}) {
  const summary = metrics?.summary ?? {};
  const metricItems = [
    { key: 'draft_total', label: '草案生成数', value: metricCount(summary.draft_total) },
    { key: 'draft_adoption_rate', label: '草案确认率', value: metricPercent(summary.draft_adoption_rate) },
    { key: 'chat_run_success_rate', label: 'AI 生成成功率', value: metricPercent(summary.chat_run_success_rate) },
    { key: 'chat_run_cancel_rate', label: 'AI 生成取消率', value: metricPercent(summary.chat_run_cancel_rate) },
    { key: 'draft_user_modified_count', label: '用户修改率', value: metricPercent(summary.draft_user_modified_rate) },
    { key: 'reference_usage_rate', label: '@ 引用使用率', value: metricPercent(summary.reference_usage_rate) },
    { key: 'scheduled_job_run_success_rate', label: '作业运行成功率', value: metricPercent(summary.scheduled_job_run_success_rate) },
    { key: 'failed_run_repaired_count', label: '失败修复率', value: metricPercent(summary.failed_run_repair_rate) },
    { key: 'knowledge_reference_hit_count', label: '知识引用命中率', value: metricPercent(summary.knowledge_reference_hit_rate) },
  ];
  const draftStatusItems = [
    { label: '待确认', value: metricCount(summary.draft_pending_count) },
    { label: '已应用', value: metricCount(summary.draft_confirmed_count) },
    { label: '已取消', value: metricCount(summary.draft_cancelled_count) },
    { label: '已过期', value: metricCount(summary.draft_expired_count) },
    { label: '失败', value: metricCount(summary.draft_failed_count) },
  ];
  const draftActionItems = metrics?.drafts_by_action ?? [];
  const runAttributionItems = metrics?.scheduled_job_run_attribution?.items ?? [];
  const funnelStages = [...(metrics?.funnel?.stages ?? [])].sort(
    (left, right) => Number(left.sort_order ?? 0) - Number(right.sort_order ?? 0),
  );
  const runTrackingItems = [
    {
      label: 'AI 生成',
      value: `成功 ${metricCount(summary.chat_run_succeeded_count)} · 取消 ${metricCount(
        summary.chat_run_cancelled_count,
      )} · 失败 ${metricCount(summary.chat_run_failed_count)} · 运行中 ${metricCount(
        summary.chat_run_running_count,
      )} · 总数 ${metricCount(summary.chat_run_total)}`,
    },
    {
      label: '生成质量',
      value: `失败率 ${metricPercent(summary.chat_run_failure_rate)} · 平均耗时 ${metricDurationMs(
        summary.chat_run_average_duration_ms,
      )} · 模型失败 ${metricCount(summary.chat_run_model_failed_count)} (${metricPercent(
        summary.chat_run_model_failure_rate,
      )})`,
    },
    {
      label: '作业运行',
      value: `成功 ${metricCount(summary.scheduled_job_run_succeeded_count)} · 失败 ${metricCount(
        summary.scheduled_job_run_failed_count,
      )} · 总数 ${metricCount(summary.scheduled_job_run_total)}`,
    },
    {
      label: '失败修复',
      value: `已修复 ${metricCount(summary.failed_run_repaired_count)} · 失败运行 ${metricCount(
        summary.failed_run_total,
      )}`,
    },
    ...(runAttributionItems.length
      ? [
          {
            label: '归因来源',
            value: runAttributionItems
              .map((item) => `${item.label} ${metricCount(item.count)}`)
              .join(' · '),
          },
        ]
      : []),
  ];
  const referenceTrackingItems = [
    {
      label: '用户消息',
      value: `已引用 ${metricCount(summary.referenced_user_message_count)} · 用户消息 ${metricCount(
        summary.user_message_total,
      )}`,
    },
    {
      label: '知识命中',
      value: `命中 ${metricCount(summary.knowledge_reference_hit_count)} · 请求 ${metricCount(
        summary.knowledge_reference_request_count,
      )} · 知识引用 ${metricCount(summary.knowledge_reference_count)}`,
    },
  ];

  return (
    <div className="assistant-metrics-panel">
      <div className="assistant-metrics-header">
        <Space size={6}>
          <BarChartOutlined />
          <Text strong>助手效果指标</Text>
        </Space>
        <Space size={8} wrap>
          <Segmented
            aria-label="指标时间范围"
            disabled={isLoading}
            options={[
              { label: '全部', value: 'all' },
              { label: '7天', value: '7' },
              { label: '30天', value: '30' },
              { label: '90天', value: '90' },
            ]}
            size="small"
            value={windowDays ? String(windowDays) : 'all'}
            onChange={(value) => {
              const nextValue = value === 'all' ? undefined : Number(value);
              onChangeWindow(nextValue);
            }}
          />
          <Button loading={isLoading} size="small" onClick={onRefresh}>
            {metrics ? '刷新指标' : '查看指标'}
          </Button>
        </Space>
      </div>
      {metrics ? (
        <>
          <div className="assistant-metrics-grid">
            {metricItems.map((item) => (
              <button
                aria-label={`指标 ${item.label}`}
                className={`assistant-metric-item assistant-metric-button${
                  metricDetails?.metric === item.key ? ' assistant-metric-button-active' : ''
                }`}
                key={item.key}
                type="button"
                onClick={() => onOpenDetail(item.key)}
              >
                <Text type="secondary">{item.label}</Text>
                <Text strong>{item.value}</Text>
              </button>
            ))}
          </div>
          {metrics.instrumentation?.notes?.length ? (
            <div className="assistant-metrics-instrumentation" aria-label="指标口径说明">
              {metrics.instrumentation.notes.map((note) => (
                <Text key={note.code ?? note.message} type="secondary">
                  {note.message}
                </Text>
              ))}
              {metrics.instrumentation.view_metrics ? (
                <Space size={[4, 4]} wrap>
                  <Tag>{`埋点查看 ${metricCount(metrics.instrumentation.view_metrics.tracked_count)}`}</Tag>
                  <Tag>{`历史推断 ${metricCount(metrics.instrumentation.view_metrics.inferred_legacy_count)}`}</Tag>
                </Space>
              ) : null}
            </div>
          ) : null}
          <div className="assistant-metrics-breakdown" aria-label="指标明细">
            <div className="assistant-metrics-detail-header">
              <Text strong>{metricDetails?.title ?? '指标明细'}</Text>
              {isDetailLoading ? <Spin size="small" /> : <Tag>{metricDetails?.total ?? 0} 条</Tag>}
            </div>
            {metricDetails?.items?.length ? (
              <div className="assistant-metrics-detail-list">
                {metricDetails.items.map((item) => (
                  <div
                    aria-label={`指标明细 ${item.title}`}
                    className="assistant-metrics-detail-item"
                    key={`${item.type}:${item.id}`}
                  >
                    <div className="assistant-metrics-detail-title">
                      <Text strong>{item.title}</Text>
                      {item.status ? <Tag>{item.status}</Tag> : null}
                    </div>
                    {item.description ? (
                      <Text type="secondary">{item.description}</Text>
                    ) : null}
                    <Space size={[4, 4]} wrap>
                      <Tag>{item.type}</Tag>
                      {item.action ? <Tag>{item.action}</Tag> : null}
                      {item.updated_at ?? item.created_at ? (
                        <Tag>{item.updated_at ?? item.created_at}</Tag>
                      ) : null}
                      {item.url ? (
                        <a href={item.url}>查看来源</a>
                      ) : null}
                    </Space>
                  </div>
                ))}
              </div>
            ) : (
              <Text type="secondary">
                {isDetailLoading ? '正在加载明细...' : '点击上方指标查看对应草案、运行或引用明细。'}
              </Text>
            )}
          </div>
          {funnelStages.length ? (
            <div className="assistant-metrics-breakdown">
              <Text strong>效果漏斗</Text>
              <div className="assistant-metrics-action-list">
                {funnelStages.map((stage) => (
                  <Text
                    aria-label={`效果漏斗 ${stage.label}`}
                    key={stage.key}
                    type="secondary"
                  >
                    {stage.label}：{metricCount(stage.count)}
                  </Text>
                ))}
              </div>
            </div>
          ) : null}
          <div className="assistant-metrics-breakdown">
            <Text strong>草案状态</Text>
            <Space size={[4, 4]} wrap>
              {draftStatusItems.map((item) => (
                <Tag aria-label={`草案状态 ${item.label}`} key={item.label}>
                  {item.label} {item.value}
                </Tag>
              ))}
            </Space>
          </div>
          {draftActionItems.length ? (
            <div className="assistant-metrics-breakdown">
              <Text strong>草案类型</Text>
              <div className="assistant-metrics-action-list">
                {draftActionItems.map((item) => (
                  <Text
                    aria-label={`草案类型 ${item.action}`}
                    key={item.action}
                    type="secondary"
                  >
                    {assistantDraftActionLabel(item.action)}：总数 {metricCount(item.total)}
                    {' · '}待确认 {metricCount(item.pending_count)}
                    {' · '}已应用 {metricCount(item.confirmed_count)}
                    {' · '}已取消 {metricCount(item.cancelled_count)}
                    {' · '}处理率 {metricRatio(
                      Number(item.total ?? 0) - Number(item.pending_count ?? 0),
                      Number(item.total ?? 0),
                    )}
                  </Text>
                ))}
              </div>
            </div>
          ) : null}
          <div className="assistant-metrics-breakdown">
            <Text strong>运行追踪</Text>
            <div className="assistant-metrics-action-list">
              {runTrackingItems.map((item) => (
                <Text
                  aria-label={`运行追踪 ${item.label}`}
                  key={item.label}
                  type="secondary"
                >
                  {item.label}：{item.value}
                </Text>
              ))}
            </div>
          </div>
          <div className="assistant-metrics-breakdown">
            <Text strong>引用追踪</Text>
            <div className="assistant-metrics-action-list">
              {referenceTrackingItems.map((item) => (
                <Text
                  aria-label={`引用追踪 ${item.label}`}
                  key={item.label}
                  type="secondary"
                >
                  {item.label}：{item.value}
                </Text>
              ))}
            </div>
          </div>
        </>
      ) : (
        <Text type="secondary">跟踪草案、引用、运行和失败修复效果。</Text>
      )}
    </div>
  );
}
