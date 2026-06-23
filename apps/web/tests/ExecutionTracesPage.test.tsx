import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import ExecutionTracesPage from '../src/pages/ExecutionTraces';

function installExecutionTracesFetchMock() {
  const trace = {
    duration_ms: 8000,
    failed_node_count: 0,
    id: 'scheduled_job_run_trace',
    node_count: 6,
    related_ids: {
      ai_executor_task: ['ai_executor_task_trace'],
      audit_event: ['audit_trace'],
      code_inspection_report: ['code_inspection_report_trace'],
      model_gateway_log: ['model_gateway_log_trace'],
      plugin_invocation_log: ['plugin_invocation_log_trace'],
      scheduled_job_run: ['scheduled_job_run_trace'],
    },
    root_id: 'scheduled_job_run_trace',
    root_type: 'scheduled_job_run',
    running_node_count: 0,
    started_at: '2026-06-20T01:00:00Z',
    status: 'succeeded',
    summary: '代码仓库质量安全规范巡检完成。',
    title: '定时作业运行 scheduled_job_run_trace',
    updated_at: '2026-06-20T01:00:08Z',
  };
  const detail = {
    ...trace,
    edges: [
      {
        from: 'scheduled_job_run:scheduled_job_run_trace',
        label: 'invokes',
        to: 'plugin_invocation_log:plugin_invocation_log_trace',
      },
      {
        from: 'plugin_invocation_log:plugin_invocation_log_trace',
        label: 'dispatches',
        to: 'ai_executor_task:ai_executor_task_trace',
      },
    ],
    nodes: [
      {
        duration_ms: 8000,
        error_code: null,
        error_message: null,
        finished_at: '2026-06-20T01:00:08Z',
        id: 'scheduled_job_run:scheduled_job_run_trace',
        label: '定时作业运行',
        metadata: { scheduled_job_id: 'scheduled_job_trace' },
        source_id: 'scheduled_job_run_trace',
        source_type: 'scheduled_job_run',
        started_at: '2026-06-20T01:00:00Z',
        status: 'succeeded',
        summary: '代码仓库质量安全规范巡检完成。',
      },
      {
        duration_ms: 1200,
        error_code: null,
        error_message: null,
        finished_at: '2026-06-20T01:00:02Z',
        id: 'plugin_invocation_log:plugin_invocation_log_trace',
        label: '插件调用',
        metadata: { request_summary: { headers: { Authorization: '<redacted>' } } },
        source_id: 'plugin_invocation_log_trace',
        source_type: 'plugin_invocation_log',
        started_at: '2026-06-20T01:00:01Z',
        status: 'succeeded',
        summary: 'succeeded',
      },
      {
        duration_ms: 900,
        error_code: null,
        error_message: null,
        finished_at: '2026-06-20T01:00:04Z',
        id: 'model_gateway_log:model_gateway_log_trace',
        label: '模型网关调用',
        metadata: { model: 'gpt-5.5', provider: 'openai_compatible' },
        source_id: 'model_gateway_log_trace',
        source_type: 'model_gateway_log',
        started_at: '2026-06-20T01:00:03Z',
        status: 'succeeded',
        summary: 'openai_compatible/gpt-5.5',
      },
    ],
  };
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    const url = String(input);
    if (url.startsWith('/api/governance/execution-traces?') && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [trace],
          page: 1,
          page_size: 10,
          total: 1,
        },
      });
    }
    if (input === '/api/governance/execution-traces/scheduled_job_run_trace' && init?.method === 'GET') {
      return jsonResponse({ data: detail });
    }
    throw new Error(`Unexpected fetch call: ${String(input)}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);
  return { fetchMock };
}

describe('ExecutionTracesPage', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('loads traces and opens the node detail dialog', async () => {
    installExecutionTracesFetchMock();

    render(<ExecutionTracesPage />);

    await screen.findByText('定时作业运行 scheduled_job_run_trace');
    expect(screen.getAllByText('成功').length).toBeGreaterThan(0);
    expect(screen.getAllByText('定时作业运行').length).toBeGreaterThan(0);
    expect(screen.getAllByText('2026-06-20 09:00').length).toBeGreaterThan(0);
    expect(screen.getByText('8.00 s')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '详情' }));

    const dialog = await screen.findByRole('dialog', { name: '执行诊断详情' });
    await waitFor(() => expect(within(dialog).getByText('执行节点')).toBeInTheDocument());

    expect(within(dialog).getByText('节点关系')).toBeInTheDocument();
    expect(within(dialog).getAllByText('插件调用').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('模型网关调用').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('plugin_invocation_log_trace').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('model_gateway_log_trace').length).toBeGreaterThan(0);
    expect(within(dialog).getByText('dispatches')).toBeInTheDocument();
    expect(within(dialog).queryByText('secret-run-token')).not.toBeInTheDocument();
  });
});
