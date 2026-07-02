import { afterEach, describe, expect, it, vi } from 'vitest';

import { timeoutAiExecutorTasks } from '../src/services/systemOperationsClient';

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('system operations client', () => {
  it('calls runner timeout scan and preserves summary next actions', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(input).toBe('/api/system/ai-executor-tasks/timeout-scan');
      expect(init?.method).toBe('POST');
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      expect(init?.body).toBe(JSON.stringify({ now: '2099-01-01T00:00:00+00:00' }));
      return new Response(
        JSON.stringify({
          data: {
            dead_letter_task_ids: ['task_dead'],
            next_actions: [
              {
                description: '死信任务已超过最大重派次数，需要查看日志、修复 Runner 或手动重试。',
                key: 'inspect_dead_letter_tasks',
                label: '查看死信任务日志',
                severity: 'error',
                task_ids: ['task_dead'],
              },
            ],
            requeued_task_ids: [],
            summary: {
              dead_letter_count: 1,
              manual_attention_required: true,
              message: '发现需要人工处理的 Runner 任务，请查看死信或超时任务日志。',
              requeued_count: 0,
              scanned_at: '2099-01-01T00:00:00+00:00',
              status: 'attention_required',
              timed_out_count: 0,
              total_affected: 1,
            },
            tasks: [{ id: 'task_dead', status: 'dead_letter' }],
            timed_out_task_ids: [],
          },
        }),
        {
          headers: { 'Content-Type': 'application/json' },
          status: 200,
        },
      );
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      timeoutAiExecutorTasks({ now: '2099-01-01T00:00:00+00:00' }),
    ).resolves.toMatchObject({
      dead_letter_task_ids: ['task_dead'],
      next_actions: [
        expect.objectContaining({
          key: 'inspect_dead_letter_tasks',
          label: '查看死信任务日志',
        }),
      ],
      summary: {
        dead_letter_count: 1,
        manual_attention_required: true,
        message: '发现需要人工处理的 Runner 任务，请查看死信或超时任务日志。',
        requeued_count: 0,
        scanned_at: '2099-01-01T00:00:00+00:00',
        status: 'attention_required',
        timed_out_count: 0,
        total_affected: 1,
      },
    });
  });
});
