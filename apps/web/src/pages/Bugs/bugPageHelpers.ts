import type { ClipboardEvent as ReactClipboardEvent } from 'react';

import type { ManagementListQuery } from '../../components/ManagementListPage';
import type { BugRecord } from '../../data/management';
import type {
  BugImageEvidenceItem,
  BugListQuery,
  CurrentUserResponse,
} from '../../services/aiBrain';

export const severityLabels: Record<BugRecord['severity'], { color: string; label: string }> = {
  blocker: { color: 'red', label: '阻断' },
  critical: { color: 'volcano', label: '致命' },
  major: { color: 'orange', label: '严重' },
  minor: { color: 'blue', label: '一般' },
};

export const statusLabels: Record<BugRecord['status'], { color: string; label: string }> = {
  assigned: { color: 'purple', label: '已分派' },
  closed: { color: 'default', label: '已关闭' },
  fixed: { color: 'cyan', label: '已修复' },
  needs_info: { color: 'gold', label: '待补充' },
  open: { color: 'red', label: '待处理' },
  reopened: { color: 'red', label: '重新打开' },
  triaged: { color: 'gold', label: '已分诊' },
  verified: { color: 'green', label: '已验证' },
};

export const sourceLabels: Record<BugRecord['source'], { color: string; label: string }> = {
  ai_auto_test: { color: 'purple', label: 'AI 自动测试' },
  ai_post_release: { color: 'cyan', label: 'AI 上线后分析' },
  code_inspection: { color: 'magenta', label: '代码巡检' },
  manual_test: { color: 'default', label: '人工登记' },
};

export type BugFormValues = {
  assignee?: string;
  description: string;
  duplicate_of_bug_id?: string;
  evidence_json?: string;
  module_code?: string;
  product_id?: string;
  related_task_id?: string;
  reproduce_steps_text?: string;
  requirement_id?: string;
  severity: BugRecord['severity'];
  source: BugRecord['source'];
  status?: BugRecord['status'];
  title: string;
  version_id?: string;
};

export type BugBatchFormValues = {
  assignee?: string;
  reason?: string;
  severity?: BugRecord['severity'];
  status?: BugRecord['status'];
};

const bugImageEvidenceKeys: Array<keyof BugImageEvidenceItem> = [
  'bucket',
  'content_hash',
  'filename',
  'id',
  'mime_type',
  'object_key',
  'size_bytes',
  'source',
  'storage_provider',
  'uploaded_at',
  'uploaded_by',
];

export const bugImageMimeTypes = new Set(['image/gif', 'image/jpeg', 'image/png', 'image/webp']);

export function formatEvidenceJson(evidence?: Record<string, unknown>) {
  if (!evidence || Object.keys(evidence).length === 0) {
    return '';
  }
  return JSON.stringify(evidence, null, 2);
}

export function parseEvidenceJson(value?: string): Record<string, unknown> {
  const trimmed = value?.trim();
  if (!trimmed) {
    return {};
  }
  const parsed = JSON.parse(trimmed) as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('证据 JSON 请输入对象 JSON');
  }
  return parsed as Record<string, unknown>;
}

export function evidenceWithoutImages(
  evidence?: Record<string, unknown>,
): Record<string, unknown> | undefined {
  if (!evidence) {
    return undefined;
  }
  const nextEvidence = { ...evidence };
  delete nextEvidence.images;
  return nextEvidence;
}

function isBugImageEvidenceItem(value: unknown): value is BugImageEvidenceItem {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return false;
  }
  const image = value as Partial<BugImageEvidenceItem>;
  return (
    typeof image.bucket === 'string' &&
    typeof image.content_hash === 'string' &&
    typeof image.filename === 'string' &&
    typeof image.id === 'string' &&
    typeof image.mime_type === 'string' &&
    typeof image.object_key === 'string' &&
    typeof image.size_bytes === 'number' &&
    (image.source === 'clipboard' || image.source === 'file_picker') &&
    typeof image.storage_provider === 'string' &&
    typeof image.uploaded_at === 'string' &&
    typeof image.uploaded_by === 'string'
  );
}

export function evidenceImages(evidence?: Record<string, unknown>): BugImageEvidenceItem[] {
  const images = evidence?.images;
  if (!Array.isArray(images)) {
    return [];
  }
  return images.filter(isBugImageEvidenceItem);
}

export function evidenceWithImages(
  evidence: Record<string, unknown>,
  images: BugImageEvidenceItem[],
): Record<string, unknown> {
  if (images.length === 0) {
    return evidence;
  }
  return {
    ...evidence,
    images: images.map((image) =>
      bugImageEvidenceKeys.reduce<Record<string, unknown>>((payload, key) => {
        payload[key] = image[key];
        return payload;
      }, {}),
    ),
  };
}

export function readFileAsBase64(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error('图片读取失败'));
    reader.onload = () => {
      const result = typeof reader.result === 'string' ? reader.result : '';
      const [, contentBase64 = result] = result.split(',', 2);
      resolve(contentBase64);
    };
    reader.readAsDataURL(file);
  });
}

export function clipboardImageFiles(event: ReactClipboardEvent<HTMLElement>) {
  const clipboardData = event.clipboardData;
  const files = Array.from(clipboardData.files ?? []).filter((file) =>
    bugImageMimeTypes.has(file.type),
  );
  if (files.length > 0) {
    return files;
  }
  return Array.from(clipboardData.items ?? [])
    .filter((item) => item.kind === 'file' && bugImageMimeTypes.has(item.type))
    .map((item) => item.getAsFile())
    .filter((file): file is File => Boolean(file));
}

export function evidenceJsonRule() {
  return {
    validator(_: unknown, value?: string) {
      try {
        parseEvidenceJson(value);
        return Promise.resolve();
      } catch {
        return Promise.reject(new Error('证据 JSON 请输入合法对象 JSON'));
      }
    },
  };
}

export function formatReproduceSteps(steps?: string[]) {
  return steps?.join('\n') ?? '';
}

export function parseReproduceSteps(value?: string) {
  return (value ?? '')
    .split(/\r?\n/)
    .map((step) => step.trim())
    .filter(Boolean);
}

export function isFormValidationError(error: unknown) {
  return Boolean(
    error &&
      typeof error === 'object' &&
      'errorFields' in error &&
      Array.isArray((error as { errorFields?: unknown }).errorFields),
  );
}

const bugSortFieldMap: Record<string, string> = {
  assignee: 'assignee',
  createdAt: 'created_at',
  id: 'id',
  module: 'module_code',
  severity: 'severity',
  source: 'source',
  status: 'status',
  title: 'title',
  versionName: 'version_name',
};

function normalizeFilterText(value: unknown) {
  return String(value ?? '').trim() || undefined;
}

export function buildBugListQuery(query: ManagementListQuery): BugListQuery {
  return {
    module: normalizeFilterText(query.filters.module),
    page: query.page,
    pageSize: query.pageSize,
    severity: normalizeFilterText(query.filters.severity),
    sortField: query.sortField ? bugSortFieldMap[query.sortField] ?? query.sortField : undefined,
    sortOrder: query.sortOrder,
    status: normalizeFilterText(query.filters.status),
    title: normalizeFilterText(query.filters.title),
    version: normalizeFilterText(query.filters.versionName),
  };
}

export function canManageBugResources(user: CurrentUserResponse | undefined) {
  if (!user) {
    return true;
  }
  const roles = new Set(user.roles ?? []);
  const permissions = new Set(user.permissions ?? []);
  return (
    roles.has('admin') ||
    roles.has('product_owner') ||
    roles.has('rd_owner') ||
    permissions.has('system.admin') ||
    permissions.has('bug.manage')
  );
}
