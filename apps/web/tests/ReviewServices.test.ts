import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  editApproveTaskCenterReview,
  rejectTaskCenterReview,
  requestTaskCenterReviewMoreInfo,
  submitTaskCenterMoreInfo,
} from '../src/services/aiBrain';

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('review service API mappings', () => {
  it('sends review and task more-info mutations to backend APIs', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/reviews/review_api/request-more-info') {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBe(
          JSON.stringify({
            questions: ['请补充验收边界'],
            version: 1,
          }),
        );
        return jsonResponse({
          data: {
            review_status: 'requested_more_info',
            task_status: 'waiting_more_info',
          },
        });
      }
      if (input === '/api/ai-tasks/task_api/more-info') {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBe(
          JSON.stringify({
            answers: [{ answer: '补充 P0 验收边界', question: '补充说明' }],
          }),
        );
        return jsonResponse({ data: { id: 'task_api', status: 'draft' } });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      requestTaskCenterReviewMoreInfo('review_api', 1, ['请补充验收边界']),
    ).resolves.toMatchObject({
      review_status: 'requested_more_info',
      task_status: 'waiting_more_info',
    });
    await expect(
      submitTaskCenterMoreInfo('task_api', [
        { answer: '补充 P0 验收边界', question: '补充说明' },
      ]),
    ).resolves.toMatchObject({ id: 'task_api', status: 'draft' });
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toEqual([
      ['/api/reviews/review_api/request-more-info', 'POST'],
      ['/api/ai-tasks/task_api/more-info', 'POST'],
    ]);
  });

  it('sends review edit-approve and reject mutations to backend APIs', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/reviews/review_api/edit-approve') {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBe(
          JSON.stringify({
            edited_content: { summary: '人工修订后的技术方案' },
            version: 1,
          }),
        );
        return jsonResponse({
          data: {
            review_status: 'edited_approved',
            task_status: 'completed',
          },
        });
      }
      if (input === '/api/reviews/review_api/reject') {
        expect(init?.method).toBe('POST');
        expect(init?.body).toBe(
          JSON.stringify({
            decision_reason: '风险过高，需要重新生成',
            version: 2,
          }),
        );
        return jsonResponse({
          data: {
            review_status: 'rejected',
            task_status: 'failed',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      editApproveTaskCenterReview('review_api', 1, { summary: '人工修订后的技术方案' }),
    ).resolves.toMatchObject({
      review_status: 'edited_approved',
      task_status: 'completed',
    });
    await expect(
      rejectTaskCenterReview('review_api', 2, '风险过高，需要重新生成'),
    ).resolves.toMatchObject({
      review_status: 'rejected',
      task_status: 'failed',
    });
    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toEqual([
      ['/api/reviews/review_api/edit-approve', 'POST'],
      ['/api/reviews/review_api/reject', 'POST'],
    ]);
  });
});
