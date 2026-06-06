import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import TaskCenterPage from '../src/pages/TaskCenter';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  void message.destroy();
  notification.destroy();
  Modal.destroyAll();
});

describe('TaskCenterPage', () => {
  it('opens a Code Review report with a requirement full-chain link', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/reviews/pending') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products?active_only=true') {
        return jsonResponse({
          data: {
            items: [{ code: 'AI-BRAIN', id: 'product_api', name: 'AI Brain 产品' }],
            total: 1,
          },
        });
      }
      if (input === '/api/product-versions?active_only=true') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (typeof input === 'string' && input.startsWith('/api/ai-tasks?page=1&page_size=10')) {
        return jsonResponse({
          data: {
            items: [
              {
                created_at: '2026-06-04T09:00:00+00:00',
                id: 'task_code_review',
                owner: 'user_admin',
                product_id: 'product_api',
                product_name: 'AI Brain 产品',
                requirement_id: 'requirement_api',
                status: 'waiting_review',
                task_type: 'code_review',
                title: 'Code Review：接口任务',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      if (input === '/api/ai-tasks/task_code_review/code-review-report') {
        return jsonResponse({
          data: {
            findings: [
              {
                file_path: 'apps/api/app/main.py',
                line_number: 42,
                severity: 'high',
                summary: '缺少边界测试',
              },
            ],
            gitlab_writeback_performed: false,
            id: 'report_api',
            risk_level: 'medium',
            status: 'pending_review',
            summary: '发现 1 个高风险问题',
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<TaskCenterPage />);

    const codeReviewTaskRow = (await screen.findByText('Code Review：接口任务')).closest('tr');
    expect(codeReviewTaskRow).not.toBeNull();
    fireEvent.click(within(codeReviewTaskRow as HTMLElement).getByRole('button', { name: '操作' }));
    const operationDialog = await screen.findByTestId('task-operation-dialog');
    fireEvent.click(within(operationDialog).getByRole('button', { name: '查看报告' }));

    expect(await screen.findByText('发现 1 个高风险问题')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '查看需求全链路' })).toHaveAttribute(
      'href',
      '/delivery/requirements/requirement_api/full-chain',
    );
  });
});
