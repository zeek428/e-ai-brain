import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { RequirementAssessmentDrawer } from '../src/pages/Requirements/RequirementAssessmentDrawer';

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

describe('RequirementAssessmentDrawer', () => {
  it('starts assessment from the requirement revision and keeps delivery at the policy boundary', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.spyOn(message, 'success').mockImplementation(() => null as never);
    const bodies: unknown[] = [];
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input), 'http://localhost');
      const method = init?.method ?? 'GET';
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (url.pathname === '/api/requirements/requirement_001' && method === 'GET') {
        return jsonResponse({ data: { assessment_revision: 3, id: 'requirement_001', status: 'submitted', title: '受控研发需求' } });
      }
      if (url.pathname === '/api/requirements/requirement_001/assessments/latest' && method === 'GET') {
        return jsonResponse({ detail: { code: 'NOT_FOUND', message: 'missing' } }, 404);
      }
      if (url.pathname === '/api/requirements/requirement_001/assessments' && method === 'POST') {
        bodies.push(JSON.parse(String(init?.body)));
        return jsonResponse({
          data: {
            id: 'assessment_001',
            opinion_round: 1,
            opinions: [],
            requirement_id: 'requirement_001',
            requirement_revision: 3,
            status: 'evaluating',
            version: 1,
          },
        });
      }
      throw new Error(`Unexpected ${method} ${url.pathname}`);
    }));

    render(
      <RequirementAssessmentDrawer
        open
        requirementId="requirement_001"
        requirementTitle="受控研发需求"
        onChanged={vi.fn()}
        onClose={vi.fn()}
      />,
    );

    expect(await screen.findByText('启动需求评估')).toBeInTheDocument();
    expect(screen.getByText(/高风险、策略冲突和归组并列会自动停在人工决策点/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '启动需求评估' }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({ requirement_revision: 3 });
    expect(screen.getByText('评估中')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '部署' })).not.toBeInTheDocument();
  });

  it('submits human clarification with the frozen assessment version', async () => {
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.spyOn(message, 'success').mockImplementation(() => null as never);
    const bodies: unknown[] = [];
    vi.stubGlobal('fetch', vi.fn<typeof fetch>(async (input, init) => {
      const url = new URL(String(input), 'http://localhost');
      const method = init?.method ?? 'GET';
      if (url.pathname === '/api/requirements/requirement_001' && method === 'GET') {
        return jsonResponse({ data: { assessment_revision: 3, id: 'requirement_001', status: 'submitted', title: '受控研发需求' } });
      }
      if (url.pathname === '/api/requirements/requirement_001/assessments/latest' && method === 'GET') {
        return jsonResponse({
          data: {
            id: 'assessment_001',
            opinion_round: 1,
            opinions: [],
            requirement_id: 'requirement_001',
            requirement_revision: 3,
            status: 'needs_info',
            version: 5,
          },
        });
      }
      if (url.pathname === '/api/requirement-assessments/assessment_001/answers' && method === 'POST') {
        bodies.push(JSON.parse(String(init?.body)));
        return jsonResponse({ data: { id: 'assessment_001', requirement_id: 'requirement_001', requirement_revision: 3, status: 'evaluating', version: 6 } });
      }
      throw new Error(`Unexpected ${method} ${url.pathname}`);
    }));

    render(<RequirementAssessmentDrawer open requirementId="requirement_001" onChanged={vi.fn()} onClose={vi.fn()} />);

    fireEvent.click(await screen.findByRole('button', { name: '补充评估信息' }));
    fireEvent.change(screen.getByLabelText('补充说明'), { target: { value: '目标用户是企业管理员' } });
    fireEvent.click(screen.getByRole('button', { name: '提交补充信息' }));

    await waitFor(() => expect(bodies).toHaveLength(1));
    expect(bodies[0]).toMatchObject({
      answers: { additional_context: '目标用户是企业管理员' },
      expected_version: 5,
    });
  });
});
