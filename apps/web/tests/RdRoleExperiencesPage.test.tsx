import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import RdRoleExperiencesPage from '../src/pages/RdRoleExperiences';

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    headers: { 'Content-Type': 'application/json' },
    status,
  });
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe('RdRoleExperiencesPage', () => {
  it('filters governed experiences and makes a versioned approval decision', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.spyOn(message, 'success').mockImplementation(() => null as never);
    const decisionBodies: unknown[] = [];
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input), 'http://localhost');
      const method = init?.method ?? 'GET';
      if (url.pathname === '/api/delivery/rd-role-experiences' && method === 'GET') {
        expect(url.searchParams.get('status')).toBe('pending');
        expect(url.searchParams.get('product_id')).toBe('product-a');
        return jsonResponse({
          data: {
            items: [{
              brain_app_id: 'rd_brain',
              confidence: 0.92,
              content: { guidance: '先完成支付回归测试' },
              id: 'experience_001',
              product_scope: ['product-a'],
              repository_trust_domains: ['repo:payments'],
              review_version: 3,
              risk_scope: { maximum: 'high' },
              role_code: 'developer',
              scenario: 'payments',
              status: 'pending',
              tool_trust_domains: ['tool:ci'],
              work_item_type: 'implementation',
            }],
            page: 1,
            page_size: 20,
            total: 1,
          },
        });
      }
      if (url.pathname === '/api/delivery/rd-role-experiences/experience_001/decide' && method === 'POST') {
        decisionBodies.push(JSON.parse(String(init?.body)));
        return jsonResponse({ data: { id: 'experience_001', review_version: 4, status: 'approved' } });
      }
      throw new Error(`Unexpected ${method} ${url.pathname}`);
    }));

    render(<RdRoleExperiencesPage />);

    fireEvent.change(await screen.findByLabelText('产品 ID'), { target: { value: 'product-a' } });
    fireEvent.click(screen.getByRole('button', { name: '查询经验' }));
    expect(await screen.findByText(/先完成支付回归测试/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '批准' }));
    await waitFor(() => expect(decisionBodies).toHaveLength(1));
    expect(decisionBodies[0]).toMatchObject({ decision: 'approve', version: 3 });
  });

  it('keeps the P1 page unavailable when the experience flag is off', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async () => jsonResponse({ detail: { code: 'RD_ROLE_EXPERIENCE_DISABLED', message: 'disabled' } }, 404)));

    render(<RdRoleExperiencesPage />);

    fireEvent.click(screen.getByRole('button', { name: '查询经验' }));
    expect(await screen.findByText('经验沉淀功能当前未启用')).toBeInTheDocument();
  });
});
