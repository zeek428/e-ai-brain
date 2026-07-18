import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import RdCollaborationPage from '../src/pages/RdCollaboration';

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    status: 200,
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.clear();
  window.history.pushState({}, '', '/');
});

describe('RdCollaborationPage', () => {
  it('shows work-item dependencies and resolves a frozen human decision without deployment', async () => {
    window.history.pushState({}, '', '/delivery/rd-collaboration?run_id=run_001');
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.spyOn(message, 'success').mockImplementation(() => null as never);
    const decisionBodies: unknown[] = [];
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input), 'http://localhost');
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (url.pathname === '/api/delivery/rd-collaboration-runs/run_001') {
        return jsonResponse({
          data: {
            delivery_target: 'ready_for_release',
            id: 'run_001',
            product_version_id: 'version_001',
            seats: [],
            scope: [],
            status: 'waiting_human',
            strategy_snapshot_id: 'snapshot_001',
            suspended_decision_request_id: 'decision_001',
          },
        });
      }
      if (url.pathname === '/api/delivery/rd-collaboration-runs/run_001/work-items') {
        return jsonResponse({
          data: {
            dependencies: [{ predecessor_work_item_id: 'work_design', status: 'active', successor_work_item_id: 'work_test' }],
            items: [
              { id: 'work_design', status: 'completed', title: '完成技术设计', version: 2 },
              { id: 'work_test', risk_level: 'medium', status: 'waiting_human', title: '修复测试阻塞', version: 1 },
            ],
          },
        });
      }
      if (url.pathname === '/api/delivery/decision-requests/decision_001' && method === 'GET') {
        return jsonResponse({
          data: {
            id: 'decision_001',
            options_json: [{ code: 'continue', label: '批准继续' }],
            prompt: '测试环境需要人工确认。',
            status: 'pending',
            version: 4,
          },
        });
      }
      if (url.pathname === '/api/delivery/decision-requests/decision_001/decide' && method === 'POST') {
        decisionBodies.push(JSON.parse(String(init?.body)));
        return jsonResponse({ data: { status: 'approved' } });
      }
      throw new Error(`Unexpected ${method} ${url.pathname}`);
    }));

    render(<RdCollaborationPage />);

    expect(await screen.findByText('完成技术设计')).toBeInTheDocument();
    expect(screen.getByText('前置工作项：完成技术设计')).toBeInTheDocument();
    expect(screen.getByText('远程提交后待发布')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '部署' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: '人工决策' }));
    fireEvent.click(await screen.findByRole('button', { name: '批准继续' }));
    await waitFor(() => expect(decisionBodies).toHaveLength(1));
    expect(decisionBodies[0]).toMatchObject({ selected_option: 'continue', version: 4 });
  });
});
