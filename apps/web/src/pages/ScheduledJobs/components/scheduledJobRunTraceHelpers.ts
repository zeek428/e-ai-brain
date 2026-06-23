import { type ScheduledJobRunRecord } from '../../../services/aiBrain';

export type TemplateSourceView = {
  sourceId?: string;
  sourceType?: string;
  title?: string;
};

export function isTraceRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isEmptyTraceJsonValue(value: unknown): boolean {
  return (
    value === undefined
    || value === null
    || value === ''
    || (Array.isArray(value) && value.length === 0)
    || (typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === 0)
  );
}

export function formatTraceJsonValue(value: unknown): string {
  if (isEmptyTraceJsonValue(value)) {
    return '暂无数据';
  }
  return JSON.stringify(value, null, 2);
}

export function getRunExecutionNode(run: ScheduledJobRunRecord, nodeKey: string): unknown {
  const nodes = run.result_summary?.execution_nodes;
  if (isTraceRecord(nodes)) {
    return nodes[nodeKey];
  }
  return undefined;
}

export function nodeFieldText(value: unknown): string | undefined {
  if (typeof value === 'string' && value) {
    return value;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return undefined;
}

function nodeNestedValue(node: Record<string, unknown>, path: string): unknown {
  return path.split('.').reduce<unknown>((current, key) => {
    if (!isTraceRecord(current)) {
      return undefined;
    }
    return current[key];
  }, node);
}

export function nodeNestedFieldText(node: Record<string, unknown>, path: string): string | undefined {
  const value = nodeNestedValue(node, path);
  if (Array.isArray(value)) {
    const primitiveValues = value.filter((item) => ['string', 'number', 'boolean'].includes(typeof item));
    return primitiveValues.length ? primitiveValues.join('、') : undefined;
  }
  return nodeFieldText(value);
}

export function nodeNestedArrayCountText(node: Record<string, unknown>, path: string): string | undefined {
  const value = nodeNestedValue(node, path);
  return Array.isArray(value) ? String(value.length) : undefined;
}

export function runNodeTagColor(status: string | undefined): string {
  if (status === 'succeeded') {
    return 'green';
  }
  if (status === 'failed') {
    return 'red';
  }
  if (status === 'skipped') {
    return 'default';
  }
  return 'blue';
}

export function templateSourceFromConfig(configJson: Record<string, unknown> | undefined): TemplateSourceView | undefined {
  const rawTemplateSource = configJson?.template_source;
  if (!isTraceRecord(rawTemplateSource)) {
    return undefined;
  }
  const source = {
    sourceId: nodeFieldText(rawTemplateSource.source_id),
    sourceType: nodeFieldText(rawTemplateSource.source_type),
    title: nodeFieldText(rawTemplateSource.title),
  };
  return source.sourceId || source.sourceType || source.title ? source : undefined;
}
