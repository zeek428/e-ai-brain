import type {
  ExecutionTraceDetailRecord,
  ExecutionTraceNodeRecord,
} from '../services/diagnosticsClient';

const ATTENTION_NODE_STATUSES = new Set(['cancelled', 'failed', 'pending', 'queued', 'running']);
const DIAGNOSTIC_NODE_LIMIT = 5;

export function executionTraceAttentionNodes(detail: ExecutionTraceDetailRecord) {
  return detail.diagnostic_nodes?.length
    ? detail.diagnostic_nodes
    : detail.nodes.filter((node) => ATTENTION_NODE_STATUSES.has(node.status));
}

export function buildExecutionTraceNodeDiagnosticPrompt(
  detail: ExecutionTraceDetailRecord,
  node: ExecutionTraceNodeRecord,
  sourceTypeLabel: (value?: string | null) => string,
) {
  return [
    `请基于执行诊断链路「${detail.title}」继续排查。`,
    `重点分析节点：${sourceTypeLabel(node.source_type)} ${node.source_id}，当前状态 ${node.status}。`,
    node.error_message ? `错误信息：${node.error_message}` : '',
    node.summary ? `摘要：${node.summary}` : '',
    '请给出可能原因、需要查看的证据和修复步骤。',
  ].filter(Boolean).join('\n');
}

export function buildExecutionTraceDiagnosticPrompt(
  detail: ExecutionTraceDetailRecord,
  attentionNodes: ExecutionTraceNodeRecord[],
  sourceTypeLabel: (value?: string | null) => string,
) {
  const relatedSummary = Object.entries(detail.related_ids ?? {})
    .filter(([, ids]) => ids.length > 0)
    .slice(0, 8)
    .map(([sourceType, ids]) => `${sourceTypeLabel(sourceType)}: ${ids.slice(0, 5).join(', ')}`)
    .join('\n');
  const nodeLines = attentionNodes.slice(0, DIAGNOSTIC_NODE_LIMIT).length
    ? attentionNodes.slice(0, DIAGNOSTIC_NODE_LIMIT).map((node, index) => (
        [
          `${index + 1}. ${sourceTypeLabel(node.source_type)} ${node.source_id}`,
          `状态: ${node.status}`,
          node.error_code ? `错误码: ${node.error_code}` : '',
          node.error_message ? `错误: ${node.error_message}` : '',
          node.summary ? `摘要: ${node.summary}` : '',
        ].filter(Boolean).join('；')
      )).join('\n')
    : '未发现失败、取消、运行中或排队节点。';
  return [
    `请基于执行诊断链路「${detail.title}」分析运行问题。`,
    `链路: ${detail.id}，根对象: ${sourceTypeLabel(detail.root_type)} ${detail.root_id}，状态: ${detail.status}。`,
    `节点统计: ${detail.node_count} 个节点，${detail.failed_node_count} 个失败，耗时 ${detail.duration_ms ?? '-'} ms。`,
    detail.summary ? `链路摘要: ${detail.summary}` : '',
    relatedSummary ? `关联对象:\n${relatedSummary}` : '',
    `重点诊断节点:\n${nodeLines}`,
    '请按“最可能原因 / 需要查看的证据 / 修复步骤 / 是否可重试”输出建议。',
  ].filter(Boolean).join('\n\n');
}
