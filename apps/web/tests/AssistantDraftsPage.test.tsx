import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import AssistantDraftsPage from '../src/pages/AssistantDrafts';

function installAssistantDraftsFetchMock(options: { includeFailed?: boolean } = {}) {
  const draftRow = {
    action: 'create_scheduled_job',
    confirmed_at: null,
    created_at: '2026-06-20T02:00:00Z',
    created_by: 'user_admin',
    expires_at: null,
    id: 'assistant_action_draft_001',
    audit_event_count: 1,
    failure_count: 0,
    impact_changed_field_count: 3,
    impact_operation: 'create',
    impact_resource_id: null,
    impact_resource_type: 'scheduled_job',
    latest_audit_event_at: '2026-06-20T02:20:00Z',
    latest_audit_event_type: 'assistant_action_draft.created',
    modified_field_count: 2,
    permission_issue_count: 0,
    permission_status: 'passed',
    retry_count: 0,
    result_id: null,
    result_run_id: null,
    result_status: null,
    result_type: null,
    risk_level: 'medium',
    source_link: '/assistant?draft_id=assistant_action_draft_001',
    source_message_id: 'assistant_message_001',
    status: 'pending',
    title: '每周用户反馈洞察草案',
    updated_at: '2026-06-20T02:30:00Z',
    user_modified: true,
    validation_issue_count: 1,
    validation_status: 'warning',
    view_count: 3,
    wizard_step_count: 5,
  };
  const failedDraftRow = {
    ...draftRow,
    id: 'assistant_action_draft_failed',
    modified_field_count: 0,
    result_run_id: 'assistant_action_run_failed',
    result_status: 'failed',
    source_link: '/assistant?draft_id=assistant_action_draft_failed',
    source_message_id: 'assistant_message_failed',
    status: 'failed',
    title: '失败草案',
    updated_at: '2026-06-20T03:00:00Z',
    user_modified: false,
    validation_issue_count: 0,
    validation_status: 'passed',
    view_count: 1,
    wizard_step_count: 1,
  };
  const rows = options.includeFailed ? [draftRow, failedDraftRow] : [draftRow];
  const detail = {
    action: 'create_scheduled_job',
    created_at: '2026-06-20T02:00:00Z',
    created_by: 'user_admin',
    id: 'assistant_action_draft_001',
    metadata_json: {
      modified_fields: ['cron_expression', 'plugin_action_id'],
      view_count: 4,
    },
    governance: {
      audit: {
        event_count: 1,
        event_types: ['assistant_action_draft.created'],
        latest_actor_id: 'user_admin',
        latest_event_at: '2026-06-20T02:20:00Z',
        latest_event_id: 'audit_001',
        latest_event_type: 'assistant_action_draft.created',
      },
      diff: {
        changed_fields: [
          { change_type: 'create', field: 'cron_expression', label: 'Cron 表达式' },
        ],
        count: 1,
      },
      impact: {
        changed_field_count: 1,
        operation: 'create',
        payload_field_count: 3,
        resource_id: null,
        resource_type: 'scheduled_job',
      },
      permissions: {
        issue_count: 1,
        issues: [
          {
            field: 'plugin_action_id',
            message: '缺少插件动作管理权限',
            repair_action: {
              action: 'request_permission',
              label: '申请插件权限',
            },
            severity: 'warning',
          },
        ],
        missing_permissions: ['plugin.actions.manage'],
        required_permissions: ['system.scheduled_jobs.manage', 'plugin.actions.manage'],
        status: 'warning',
      },
      retries: {
        can_retry: false,
        failure_count: 0,
        retry_reason: '首次生成，无需重试',
        retry_count: 0,
      },
      risk: {
        level: 'medium',
        reason: '定时作业会创建新的自动化写入入口，确认前需核对调度和插件动作。',
      },
    },
    payload: {
      config_json: {
        assistant_run_once_request: {
          requested: true,
        },
      },
      cron_expression: '0 9 * * MON',
      name: '每周用户反馈洞察',
    },
    preview: {
      diffs: [
        {
          change_type: 'create',
          current: null,
          field: 'cron_expression',
          label: 'Cron 表达式',
          proposed: '0 9 * * MON',
        },
      ],
      target: {
        operation: 'create',
        resource_type: 'scheduled_job',
      },
      validation: {
        issues: [
          {
            field: 'plugin_action_id',
            message: 'plugin_action_id is required',
            severity: 'warning',
          },
        ],
        status: 'warning',
      },
    },
    risk_level: 'medium',
    source_message_id: 'assistant_message_001',
    status: 'pending',
    title: '每周用户反馈洞察草案',
    updated_at: '2026-06-20T02:30:00Z',
    wizard_steps: [{ key: 'source' }],
  };
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    const url = String(input);
    if (url.startsWith('/api/assistant/action-drafts?') && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: rows,
          page: 1,
          page_size: 10,
          summary: {
            adoption_rate: 0.25,
            draft_total: 4,
            resolution_rate: 0.5,
            status_counts: {
              cancelled: 0,
              confirmed: 1,
              expired: 0,
              failed: 1,
              pending: 2,
            },
            user_modified_count: 1,
            user_modified_rate: 0.25,
            validation_counts: {
              blocked: 0,
              passed: 3,
              unknown: 0,
              warning: 1,
            },
          },
          total: rows.length,
        },
      });
    }
    if (
      input === '/api/assistant/action-drafts/assistant_action_draft_failed/retry'
      && init?.method === 'POST'
    ) {
      expect(JSON.parse(String(init.body))).toEqual({
        reason: '从草案任务台重新打开失败草案',
      });
      return jsonResponse({
        data: {
          ...failedDraftRow,
          result_run_id: null,
          result_status: null,
          status: 'pending',
        },
      });
    }
    if (
      input === '/api/assistant/action-drafts/assistant_action_draft_001/view'
      && init?.method === 'POST'
    ) {
      return jsonResponse({ data: detail });
    }
    throw new Error(`Unexpected fetch call: ${String(input)}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);
  return { fetchMock };
}

describe('AssistantDraftsPage', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('loads draft workbench metrics and opens draft detail', async () => {
    installAssistantDraftsFetchMock();

    render(<AssistantDraftsPage />);

    await screen.findByText('每周用户反馈洞察草案');
    const summaryStrip = screen.getByRole('list', { name: '草案任务台指标' });
    expect(summaryStrip).toHaveStyle('display: grid');
    expect(summaryStrip).toHaveStyle('width: 100%');
    expect(within(summaryStrip).getAllByRole('listitem')).toHaveLength(6);
    expect(screen.getByText('待确认草案')).toBeInTheDocument();
    expect(screen.getByText('失败草案')).toBeInTheDocument();
    expect(screen.getByText('已采纳草案')).toBeInTheDocument();
    expect(screen.getByText('采纳率')).toBeInTheDocument();
    expect(screen.getAllByText('25%').length).toBeGreaterThan(0);
    expect(screen.getAllByText('待确认').length).toBeGreaterThan(0);
    expect(screen.getAllByText('警告').length).toBeGreaterThan(0);
    expect(screen.getByText('新增 · scheduled_job')).toBeInTheDocument();
    expect(screen.getByText('3 项差异')).toBeInTheDocument();
    expect(screen.getByText('1 条审计')).toBeInTheDocument();
    expect(screen.getByText('0 失败 / 0 重试')).toBeInTheDocument();
    expect(screen.getByText('2026-06-20 10:30')).toBeInTheDocument();

    const continueEditLink = screen.getByRole('link', { name: '继续编辑' });
    expect(continueEditLink).toHaveAttribute(
      'href',
      '/assistant?draft_id=assistant_action_draft_001',
    );
    expect(screen.getByRole('link', { name: '来源链路' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=assistant_message_001&source_type=assistant_message',
    );

    fireEvent.click(screen.getByRole('button', { name: '详情' }));

    const dialog = await screen.findByRole('dialog', { name: '草案详情' });
    await waitFor(() => expect(within(dialog).getByText('草案 Payload')).toBeInTheDocument());
    expect(within(dialog).getByText('执行治理摘要')).toBeInTheDocument();
    expect(within(dialog).getByText('定时作业会创建新的自动化写入入口，确认前需核对调度和插件动作。')).toBeInTheDocument();
    expect(within(dialog).getByText('执行前后差异')).toBeInTheDocument();
    expect(within(dialog).getByText(/system\.scheduled_jobs\.manage/)).toBeInTheDocument();
    expect(within(dialog).getAllByText(/plugin\.actions\.manage/).length).toBeGreaterThanOrEqual(2);
    expect(within(dialog).getByText('权限问题')).toBeInTheDocument();
    expect(within(dialog).getByText('缺少插件动作管理权限')).toBeInTheDocument();
    expect(within(dialog).getByText('申请插件权限')).toBeInTheDocument();
    expect(within(dialog).getAllByText(/assistant_action_draft.created/).length).toBeGreaterThanOrEqual(2);
    expect(within(dialog).getByText(/audit_001/)).toBeInTheDocument();
    expect(within(dialog).getByText(/操作者 user_admin/)).toBeInTheDocument();
    expect(within(dialog).getByText('不可重试')).toBeInTheDocument();
    expect(within(dialog).getByText('首次生成，无需重试')).toBeInTheDocument();
    expect(within(dialog).getAllByText('Cron 表达式').length).toBeGreaterThanOrEqual(2);
    expect(within(dialog).getByText(JSON.stringify('0 9 * * MON'))).toBeInTheDocument();
    expect(within(dialog).getByRole('link', { name: '继续编辑' })).toHaveAttribute(
      'href',
      '/assistant?draft_id=assistant_action_draft_001',
    );
    expect(within(dialog).getByText('plugin_action_id is required')).toBeInTheDocument();
    expect(within(dialog).getByText(/cron_expression/)).toBeInTheDocument();
    within(dialog).getAllByRole('link', { name: '来源链路' }).forEach((link) => {
      expect(link).toHaveAttribute(
        'href',
        '/governance/execution-traces?source_id=assistant_message_001&source_type=assistant_message',
      );
    });
  });

  it('reopens failed drafts from the workbench', async () => {
    const { fetchMock } = installAssistantDraftsFetchMock({ includeFailed: true });

    render(<AssistantDraftsPage />);

    await screen.findByText('失败草案');
    fireEvent.click(screen.getByRole('button', { name: '重新打开' }));

    const popconfirm = await screen.findByText(
      '将失败草案重新打开为待确认状态，重新确认前不会写入业务配置。是否继续？',
    );
    const popover = popconfirm.closest('.ant-popover');
    expect(popover).not.toBeNull();
    fireEvent.click(within(popover as HTMLElement).getByRole('button', { name: '重新打开' }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/assistant/action-drafts/assistant_action_draft_failed/retry',
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });
});
