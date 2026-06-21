import { type AssistantReference } from '../../services/aiBrain';

const assistantStopCommands = ['终止', '停止', '取消', 'stop', 'cancel'];

const scheduledJobRunOnceKeywords = [
  '执行一次',
  '执行一下',
  '运行一次',
  '运行一下',
  '跑一次',
  '跑一下',
  '立即执行',
  '立即运行',
  '手动执行',
  'run once',
  'run now',
  'execute once',
];

export type ActiveMentionRange = {
  endIndex: number;
  markerIndex: number;
  query: string;
};

export function activeMentionRange(value: string): ActiveMentionRange | undefined {
  const markerIndex = Math.max(value.lastIndexOf('@'), value.lastIndexOf('＠'));
  if (markerIndex < 0) {
    return undefined;
  }
  const previousChar = markerIndex > 0 ? value[markerIndex - 1] : '';
  if (previousChar && /[A-Za-z0-9._%+-]/.test(previousChar)) {
    return undefined;
  }
  const tail = value.slice(markerIndex + 1);
  if (tail.includes('\n')) {
    return undefined;
  }
  if (tail.length > 0 && /^\s/.test(tail)) {
    return undefined;
  }
  const rawQuery = tail.split(/\s+/)[0] ?? '';
  const query = rawQuery;
  const endIndex = markerIndex + 1 + rawQuery.length;
  if (!scheduledJobRunOnceRequested(value)) {
    return { endIndex, markerIndex, query };
  }
  return {
    endIndex,
    markerIndex,
    query: trimRunOnceCommandFromMentionQuery(query),
  };
}

export function activeMentionQuery(value: string) {
  return activeMentionRange(value)?.query;
}

export function assistantStopCommandRequested(value: string) {
  const normalized = value.trim().toLowerCase();
  return assistantStopCommands.some((command) => normalized === command);
}

export function scheduledJobRunOnceRequested(value: string) {
  const normalized = value.toLowerCase();
  return scheduledJobRunOnceKeywords.some((keyword) => normalized.includes(keyword));
}

export function uniqueScheduledJobReferenceCandidate(references: AssistantReference[]) {
  const scheduledJobReferences = references.filter((reference) => reference.type === 'scheduled_job');
  return scheduledJobReferences.length === 1 ? scheduledJobReferences[0] : undefined;
}

function trimRunOnceCommandFromMentionQuery(query: string) {
  const normalizedQuery = query.toLowerCase();
  let endIndex = query.length;
  scheduledJobRunOnceKeywords.forEach((keyword) => {
    const keywordIndex = normalizedQuery.indexOf(keyword);
    if (keywordIndex >= 0) {
      endIndex = Math.min(endIndex, keywordIndex);
    }
  });
  return query.slice(0, endIndex).trim().replace(/[，,。；;：:]+$/u, '');
}
