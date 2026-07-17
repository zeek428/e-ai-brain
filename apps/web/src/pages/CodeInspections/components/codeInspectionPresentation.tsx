import { Space, Tag, Typography } from 'antd';
import type { CSSProperties } from 'react';

import type { CodeInspectionFindingRecord, CodeInspectionReportRecord } from '../../../services/aiBrain';

export const riskColorByValue = new Map([
  ['critical', 'red'],
  ['high', 'orange'],
  ['medium', 'gold'],
  ['low', 'green'],
]);

export const severityColorByValue = new Map([
  ['critical', 'red'],
  ['high', 'orange'],
  ['medium', 'gold'],
  ['low', 'green'],
  ['info', 'blue'],
]);

const suppressionStatusConfig = new Map([
  ['approved', { color: 'green', label: '已忽略' }],
  ['none', { color: 'default', label: '未申请' }],
  ['pending', { color: 'gold', label: '待审批' }],
  ['rejected', { color: 'red', label: '已驳回' }],
]);

const suppressionReasonLabels = new Map([
  ['accepted_risk', '已接受风险'],
  ['baseline', '基线忽略'],
  ['false_positive', '误报'],
  ['ignored', '忽略项'],
  ['other', '其他'],
]);

const detailSingleLineTextStyle: CSSProperties = {
  display: 'block',
  maxWidth: '100%',
  overflow: 'hidden',
  textOverflow: 'ellipsis',
  whiteSpace: 'nowrap',
};

const detailMultiLineTextStyle: CSSProperties = {
  display: 'block',
  lineHeight: 1.5,
  maxWidth: '100%',
  whiteSpace: 'normal',
  wordBreak: 'break-word',
};

export function compactText(value?: string | null) {
  const text = value || '-';
  return (
    <Typography.Text ellipsis={{ tooltip: text }} style={{ display: 'block', maxWidth: '100%' }}>
      {text}
    </Typography.Text>
  );
}

export function suppressionStatusTag(status?: string | null, reason?: string | null) {
  if ((status || 'none') === 'approved' && reason === 'accepted_risk') {
    return <Tag color="orange">已接受风险</Tag>;
  }
  const config = suppressionStatusConfig.get(status || 'none') ?? {
    color: 'default',
    label: status || '未申请',
  };
  return <Tag color={config.color}>{config.label}</Tag>;
}

export function suppressionReasonText(reason?: string | null) {
  if (!reason) {
    return '-';
  }
  return suppressionReasonLabels.get(reason) ?? reason;
}

export function detailSingleLineText(value?: string | null) {
  const text = value || '-';
  return (
    <Typography.Text style={detailSingleLineTextStyle} title={text}>
      {text}
    </Typography.Text>
  );
}

function detailMultiLineText(value?: string | null) {
  const text = value || '-';
  return <Typography.Text style={detailMultiLineTextStyle}>{text}</Typography.Text>;
}

export function findingProblemText(row: CodeInspectionFindingRecord) {
  return (
    <Space orientation="vertical" size={4} style={{ width: '100%' }}>
      {detailMultiLineText(row.title)}
      {row.recommendation ? (
        <Typography.Text style={detailMultiLineTextStyle} type="secondary">
          {row.recommendation}
        </Typography.Text>
      ) : null}
    </Space>
  );
}

export function committerLabel(
  value?: {
    email?: string | null;
    finding_count?: number;
    name?: string | null;
    username?: string | null;
  } | null,
) {
  if (!value) {
    return '-';
  }
  const identity = value.name || value.username || value.email || '-';
  const email = value.email && value.email !== identity ? ` <${value.email}>` : '';
  const count = value.finding_count ? ` (${value.finding_count})` : '';
  return `${identity}${email}${count}`;
}

export function committerSummaryText(row: CodeInspectionReportRecord) {
  const summary = row.committer_summary ?? [];
  if (!summary.length) {
    return '-';
  }
  return summary.slice(0, 3).map(committerLabel).join('、');
}

export function bugLink(value?: string | null) {
  if (!value) {
    return '-';
  }
  return (
    <Typography.Link href={`/delivery/bugs?title=${encodeURIComponent(value)}`}>
      {value}
    </Typography.Link>
  );
}

export function taskLink(value?: string | null) {
  if (!value) {
    return '-';
  }
  return (
    <Typography.Link href={`/delivery/rd-tasks?task_id=${encodeURIComponent(value)}`}>
      {value}
    </Typography.Link>
  );
}

export function requirementLink(value?: string | null) {
  if (!value) {
    return '-';
  }
  return (
    <Typography.Link href={`/delivery/requirements/${encodeURIComponent(value)}/full-chain`}>
      {value}
    </Typography.Link>
  );
}
