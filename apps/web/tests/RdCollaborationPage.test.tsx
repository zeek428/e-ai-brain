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
  it('directs users without a collaboration run back to the iteration version overview', () => {
    window.history.pushState({}, '', '/delivery/rd-collaboration');

    render(<RdCollaborationPage />);

    expect(screen.getByText(/请从迭代版本总览启动或继续研发协同。/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '前往迭代版本' })).toHaveAttribute(
      'href',
      '/delivery/versions',
    );
    expect(screen.queryByLabelText('规划版本 ID')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('范围版本')).not.toBeInTheDocument();
  });

  it('shows work-item dependencies and resolves a work-item high-risk decision without deployment', async () => {
    window.history.pushState({}, '', '/delivery/rd-collaboration?run_id=run_001');
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.spyOn(message, 'success').mockImplementation(() => null as never);
    const decisionBodies: unknown[] = [];
    let decisionFetchCount = 0;
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
              {
                id: 'work_test',
                risk_level: 'high',
                status: 'waiting_human',
                suspended_decision_request_id: 'decision_001',
                title: '修复测试阻塞',
                version: 1,
              },
            ],
          },
        });
      }
      if (url.pathname === '/api/delivery/decision-requests/decision_001' && method === 'GET') {
        decisionFetchCount += 1;
        return jsonResponse({
          data: {
            id: 'decision_001',
            decision_type: 'high_risk_ai_dispatch',
            options_json: [
              { code: 'approve_dispatch' },
              { code: 'cancel_work_item' },
            ],
            prompt: '高风险 AI 派发需要人工确认。',
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
    expect(screen.getByText('snapshot_001')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '工作项 DAG（1/2）' })).toBeInTheDocument();
    expect(screen.getByText('远程提交后待发布')).toBeInTheDocument();
    expect(
      screen.getByText(/此工作台不提供部署操作/),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '部署' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: '人工决策' }));
    expect(await screen.findByText('来源工作项：修复测试阻塞')).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'approve_dispatch' })).toBeInTheDocument();
    expect(decisionFetchCount).toBe(1);
    fireEvent.click(await screen.findByRole('button', { name: 'approve_dispatch' }));
    await waitFor(() => expect(decisionBodies).toHaveLength(1));
    expect(decisionBodies[0]).toMatchObject({ selected_option: 'approve_dispatch', version: 4 });
  });

  it('lets an operator resume a cancelled work item as a new rework attempt', async () => {
    window.history.pushState({}, '', '/delivery/rd-collaboration?run_id=run_002');
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.spyOn(message, 'success').mockImplementation(() => null as never);
    const resumeBodies: unknown[] = [];
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input), 'http://localhost');
      const method = init?.method ?? 'GET';
      if (url.pathname === '/api/delivery/rd-collaboration-runs/run_002') {
        return jsonResponse({
          data: {
            delivery_target: 'ready_for_release',
            id: 'run_002',
            product_version_id: 'version_002',
            seats: [],
            scope: [],
            status: 'running',
          },
        });
      }
      if (url.pathname === '/api/delivery/rd-collaboration-runs/run_002/work-items') {
        return jsonResponse({
          data: {
            dependencies: [],
            items: [
              { id: 'work_cancelled', status: 'cancelled', title: '恢复超时实现', version: 8 },
            ],
          },
        });
      }
      if (url.pathname === '/api/delivery/rd-work-items/work_cancelled/resume' && method === 'POST') {
        resumeBodies.push(JSON.parse(String(init?.body)));
        return jsonResponse({
          data: {
            event: { event_type: 'work_item.rework_resumed' },
            next_state: 'rework_required',
            work_item: { id: 'work_cancelled', status: 'rework_required', version: 9 },
          },
        });
      }
      throw new Error(`Unexpected ${method} ${url.pathname}`);
    }));

    render(<RdCollaborationPage />);

    fireEvent.click(await screen.findByRole('button', { name: '从取消恢复' }));
    fireEvent.click(await screen.findByRole('button', { name: '确认恢复' }));

    await waitFor(() => expect(resumeBodies).toHaveLength(1));
    expect(resumeBodies[0]).toMatchObject({ version: 8 });
  });
});
