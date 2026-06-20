import { BarChartOutlined } from '@ant-design/icons';
import { Button, Space, Spin, Tag, Typography } from 'antd';

import {
  type AssistantDraftTemplate,
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
  isLoading,
  metrics,
  onRefresh,
}: {
  isLoading: boolean;
  metrics?: AssistantMetrics;
  onRefresh: () => void;
}) {
  const summary = metrics?.summary ?? {};
  const metricItems = [
    { label: '草案生成数', value: metricCount(summary.draft_total) },
    { label: '草案确认率', value: metricPercent(summary.draft_adoption_rate) },
    { label: '用户修改率', value: metricPercent(summary.draft_user_modified_rate) },
    { label: '@ 引用使用率', value: metricPercent(summary.reference_usage_rate) },
    { label: '作业运行成功率', value: metricPercent(summary.scheduled_job_run_success_rate) },
    { label: '失败修复率', value: metricPercent(summary.failed_run_repair_rate) },
    { label: '知识引用命中率', value: metricPercent(summary.knowledge_reference_hit_rate) },
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
        <Button loading={isLoading} size="small" onClick={onRefresh}>
          {metrics ? '刷新指标' : '查看指标'}
        </Button>
      </div>
      {metrics ? (
        <>
          <div className="assistant-metrics-grid">
            {metricItems.map((item) => (
              <div
                aria-label={`指标 ${item.label}`}
                className="assistant-metric-item"
                key={item.label}
              >
                <Text type="secondary">{item.label}</Text>
                <Text strong>{item.value}</Text>
              </div>
            ))}
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
