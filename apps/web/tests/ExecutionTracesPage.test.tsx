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
      result_write_record: ['result_write_record_scheduled_job_run_trace'],
      scheduled_job_run: ['scheduled_job_run_trace'],
      scheduled_job_stage: ['scheduled_job_run_trace:runner_execution'],
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
  const assistantTrace = {
    duration_ms: 5000,
    failed_node_count: 1,
    id: 'assistant_chat_run_trace',
    node_count: 3,
    related_ids: {
      ai_executor_task: [],
      assistant_chat_run: ['assistant_chat_run_trace'],
      audit_event: ['audit_assistant_trace'],
      code_inspection_report: [],
      model_gateway_log: ['model_gateway_log_assistant_trace'],
      plugin_invocation_log: [],
      scheduled_job_run: [],
    },
    root_id: 'assistant_chat_run_trace',
    root_type: 'assistant_chat_run',
    running_node_count: 0,
    started_at: '2026-06-20T02:00:00Z',
    status: 'failed',
    summary: '模型网关调用失败。',
    title: 'AI 助手运行 assistant_chat_run_trace',
    updated_at: '2026-06-20T02:00:05Z',
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
      {
        from: 'plugin_invocation_log:plugin_invocation_log_trace',
        label: 'writes_result',
        to: 'result_write_record:result_write_record_scheduled_job_run_trace',
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
      {
        duration_ms: 4600,
        error_code: null,
        error_message: null,
        finished_at: '2026-06-20T01:00:07Z',
        id: 'scheduled_job_stage:scheduled_job_run_trace:runner_execution',
        label: 'Runner 执行',
        metadata: { model_gateway_log_id: 'model_gateway_log_trace' },
        source_id: 'scheduled_job_run_trace:runner_execution',
        source_type: 'scheduled_job_stage',
        started_at: '2026-06-20T01:00:02Z',
        status: 'succeeded',
        summary: '本地执行器完成扫描。',
      },
      {
        duration_ms: null,
        error_code: null,
        error_message: null,
        finished_at: '2026-06-20T01:00:08Z',
        id: 'result_write_record:result_write_record_scheduled_job_run_trace',
        label: '结果写入记录',
        metadata: {
          records_imported: 1,
          write_target: 'code_inspection_reports',
          write_target_label: '代码巡检报告',
        },
        source_id: 'result_write_record_scheduled_job_run_trace',
        source_type: 'result_write_record',
        started_at: '2026-06-20T01:00:08Z',
        status: 'succeeded',
        summary: '代码巡检报告',
      },
    ],
  };
  const assistantDetail = {
    ...assistantTrace,
    edges: [
      {
        from: 'assistant_chat_run:assistant_chat_run_trace',
        label: 'calls_model',
        to: 'model_gateway_log:model_gateway_log_assistant_trace',
      },
    ],
    nodes: [
      {
        duration_ms: 5000,
        error_code: 'MODEL_GATEWAY_FAILED',
        error_message: '模型网关调用失败',
        finished_at: '2026-06-20T02:00:05Z',
        id: 'assistant_chat_run:assistant_chat_run_trace',
        label: 'AI 助手运行',
        metadata: { conversation_id: 'assistant_conversation_trace' },
        source_id: 'assistant_chat_run_trace',
        source_type: 'assistant_chat_run',
        started_at: '2026-06-20T02:00:00Z',
        status: 'failed',
        summary: '模型网关调用失败。',
      },
      {
        duration_ms: 1800,
        error_code: null,
        error_message: 'upstream failed',
        finished_at: '2026-06-20T02:00:03Z',
        id: 'model_gateway_log:model_gateway_log_assistant_trace',
        label: '模型网关调用',
        metadata: { model: 'gpt-5.5', provider: 'openai_compatible' },
        source_id: 'model_gateway_log_assistant_trace',
        source_type: 'model_gateway_log',
        started_at: '2026-06-20T02:00:01Z',
        status: 'failed',
        summary: 'upstream failed',
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
      const query = new URLSearchParams(url.split('?')[1] ?? '');
      if (query.get('source_id') === 'model_gateway_log_assistant_trace') {
        return jsonResponse({
          data: {
            items: [assistantTrace],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      return jsonResponse({
        data: {
          items: [trace, assistantTrace],
          page: 1,
          page_size: 10,
          total: 2,
        },
      });
    }
    if (input === '/api/governance/execution-traces/scheduled_job_run_trace' && init?.method === 'GET') {
      return jsonResponse({ data: detail });
    }
    if (input === '/api/governance/execution-traces/assistant_chat_run_trace' && init?.method === 'GET') {
      return jsonResponse({ data: assistantDetail });
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
    window.history.pushState({}, '', '/');
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('loads traces and opens the node detail dialog', async () => {
    installExecutionTracesFetchMock();

    render(<ExecutionTracesPage />);

    await screen.findByText('定时作业运行 scheduled_job_run_trace');
    expect(screen.getByText('AI 助手运行 assistant_chat_run_trace')).toBeInTheDocument();
    expect(screen.getAllByText('AI 助手运行').length).toBeGreaterThan(0);
    expect(screen.getAllByText('成功').length).toBeGreaterThan(0);
    expect(screen.getAllByText('定时作业运行').length).toBeGreaterThan(0);
    expect(screen.getAllByText('2026-06-20 09:00').length).toBeGreaterThan(0);
    expect(screen.getByText('8.00 s')).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole('button', { name: '详情' })[0]);

    const dialog = await screen.findByRole('dialog', { name: '执行诊断详情' });
    await waitFor(() => expect(within(dialog).getByText('执行节点')).toBeInTheDocument());

    expect(within(dialog).getByText('诊断建议')).toBeInTheDocument();
    expect(within(dialog).getByText(/当前链路没有失败或运行中节点/)).toBeInTheDocument();
    expect(within(dialog).getByText('节点关系')).toBeInTheDocument();
    expect(within(dialog).getAllByText('插件调用').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('定时作业阶段').length).toBeGreaterThan(0);
    expect(within(dialog).getByText('Runner 执行')).toBeInTheDocument();
    expect(within(dialog).getAllByText('模型网关调用').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('结果写入记录').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('plugin_invocation_log_trace').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('model_gateway_log_trace').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('result_write_record_scheduled_job_run_trace').length).toBeGreaterThan(0);
    expect(within(dialog).getByText('dispatches')).toBeInTheDocument();
    expect(within(dialog).getByText('writes_result')).toBeInTheDocument();
    expect(within(dialog).queryByText('secret-run-token')).not.toBeInTheDocument();
  });

  it('opens the trace detail from a source_id deep link', async () => {
    const { fetchMock } = installExecutionTracesFetchMock();
    window.history.pushState(
      {},
      '',
      '/governance/execution-traces?source_id=model_gateway_log_assistant_trace&source_type=assistant_chat_run',
    );

    render(<ExecutionTracesPage />);

    await screen.findByText('AI 助手运行 assistant_chat_run_trace');
    const dialog = await screen.findByRole('dialog', { name: '执行诊断详情' });
    await waitFor(() => expect(within(dialog).getByText('执行节点')).toBeInTheDocument());

    expect(within(dialog).getByText(/发现 2 个失败节点/)).toBeInTheDocument();
    expect(within(dialog).getAllByRole('link', { name: 'model_gateway_log_assistant_trace' }).length).toBeGreaterThan(0);
    expect(within(dialog).getAllByRole('link', { name: /问 AI/ }).length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('AI 助手运行').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('model_gateway_log_assistant_trace').length).toBeGreaterThan(0);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('source_id=model_gateway_log_assistant_trace'),
      expect.objectContaining({ method: 'GET' }),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/governance/execution-traces/assistant_chat_run_trace',
      expect.objectContaining({ method: 'GET' }),
    );
  });
});
