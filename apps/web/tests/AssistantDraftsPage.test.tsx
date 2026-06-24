import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import AssistantDraftsPage from '../src/pages/AssistantDrafts';

function installAssistantDraftsFetchMock() {
  const draftRow = {
    action: 'create_scheduled_job',
    confirmed_at: null,
    created_at: '2026-06-20T02:00:00Z',
    created_by: 'user_admin',
    expires_at: null,
    id: 'assistant_action_draft_001',
    modified_field_count: 2,
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
  const detail = {
    action: 'create_scheduled_job',
    created_at: '2026-06-20T02:00:00Z',
    created_by: 'user_admin',
    id: 'assistant_action_draft_001',
    metadata_json: {
      modified_fields: ['cron_expression', 'plugin_action_id'],
      view_count: 4,
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
          items: [draftRow],
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
          total: 1,
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
    expect(screen.getByText('待确认草案')).toBeInTheDocument();
    expect(screen.getByText('失败草案')).toBeInTheDocument();
    expect(screen.getByText('已采纳草案')).toBeInTheDocument();
    expect(screen.getByText('采纳率')).toBeInTheDocument();
    expect(screen.getAllByText('25%').length).toBeGreaterThan(0);
    expect(screen.getAllByText('待确认').length).toBeGreaterThan(0);
    expect(screen.getAllByText('警告').length).toBeGreaterThan(0);
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
    expect(within(dialog).getByText('plugin_action_id is required')).toBeInTheDocument();
    expect(within(dialog).getByText(/cron_expression/)).toBeInTheDocument();
    expect(within(dialog).getByRole('link', { name: '来源链路' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=assistant_message_001&source_type=assistant_message',
    );
  });
});
