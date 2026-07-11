import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message, Modal } from 'antd';
import { afterEach, expect, it, vi } from 'vitest';

import { ExternalEventInboxPanel } from '../src/pages/Plugins/components/ExternalEventInboxPanel';

afterEach(() => {
  Modal.destroyAll();
  message.destroy();
  cleanup();
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

it('shows redacted webhook health and retries dead-letter events', async () => {
  const retryBodies: unknown[] = [];
  const response = (body: unknown) => new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    status: 200,
  });
  vi.stubGlobal('fetch', vi.fn<typeof fetch>(async (input, init) => {
    const url = new URL(String(input), 'http://localhost');
    if (url.pathname === '/api/system/external-events' && (init?.method ?? 'GET') === 'GET') {
      return response({
        data: {
          items: [{
            attempt_count: 5,
            context: { connection_id: 'connection_github', environment: 'prod', product_id: 'product_001' },
            delivery_id: 'delivery-001',
            error_message: 'RuntimeError',
            event_type: 'workflow_run',
            id: 'external_event_001',
            payload_hash: 'hash-001',
            provider: 'github',
            received_at: '2026-07-11T02:00:00Z',
            signature_status: 'verified',
            status: 'dead_letter',
            updated_at: '2026-07-11T02:01:00Z',
          }],
          page: 1,
          page_size: 20,
          total: 1,
        },
      });
    }
    if (url.pathname === '/api/system/external-events/external_event_001/retry' && init?.method === 'POST') {
      retryBodies.push(JSON.parse(String(init.body)));
      return response({ data: { id: 'external_event_001', status: 'pending', attempt_count: 0, context: {} } });
    }
    throw new Error(`Unexpected request ${init?.method ?? 'GET'} ${url.pathname}`);
  }));
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');

  render(<ExternalEventInboxPanel />);

  expect(await screen.findByText('workflow_run')).toBeInTheDocument();
  expect(screen.getByText('死信')).toBeInTheDocument();
  expect(screen.getByText('product_001 / prod')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '重试事件 external_event_001' }));
  fireEvent.click(await screen.findByRole('button', { name: '确认重试' }));
  await waitFor(() => expect(retryBodies).toEqual([{ reason: '管理员从 Webhook 事件列表重试' }]));
});
