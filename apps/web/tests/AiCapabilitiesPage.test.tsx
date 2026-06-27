import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import AiCapabilitiesPage from '../src/pages/AiCapabilities';

function installCapabilitiesFetchMock() {
  const agentPatchBodies: unknown[] = [];
  const skillPatchBodies: unknown[] = [];
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    if (input === '/api/system/ai-skills' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              code: 'user_insight_collect',
              id: 'skill_001',
              input_schema: {
                properties: { rows: { type: 'array' } },
                type: 'object',
              },
              name: '用户洞察采集',
              output_schema: {
                properties: { insights: { type: 'array' } },
                required: ['insights'],
                type: 'object',
              },
              prompt_template: '采集用户反馈',
              requires_human_review: true,
              risk_level: 'high',
              source_type: 'form',
              status: 'active',
              version: '1.0.0',
            },
          ],
          total: 1,
        },
      });
    }
    if (input === '/api/system/ai-agents' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              code: 'insight_agent',
              default_skill_ids: ['skill_001'],
              id: 'agent_001',
              model_gateway_config_id: 'gateway_default',
              name: '洞察 Agent',
              status: 'active',
              system_prompt: '分析用户反馈',
            },
            {
              code: 'feedback_agent',
              default_skill_ids: ['skill_001'],
              id: 'agent_object_gateway',
              model_gateway_config_id: {
                default_chat_model: 'gpt-4.1-mini',
                id: 'gateway_default',
                is_default: true,
                name: '默认模型网关',
              },
              name: '反馈 Agent',
              status: 'active',
              system_prompt: '分析反馈数据',
            },
          ],
          total: 2,
        },
      });
    }
    if (input === '/api/system/model-gateway-configs' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              api_key_configured: true,
              base_url: 'https://model.example.com/v1',
              default_chat_model: 'gpt-4.1-mini',
              default_embedding_model: 'text-embedding-3-small',
              embedding_api_key_configured: true,
              embedding_connection_mode: 'reuse_chat',
              id: 'gateway_default',
              is_default: true,
              max_retries: 1,
              name: '默认模型网关',
              provider: 'openai_compatible',
              status: 'active',
              timeout_seconds: 60,
            },
          ],
          total: 1,
        },
      });
    }
    if (input === '/api/system/ai-agents/agent_001' && init?.method === 'PATCH') {
      agentPatchBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'agent_001', status: 'disabled' } });
    }
    if (input === '/api/system/ai-skills/skill_001' && init?.method === 'PATCH') {
      skillPatchBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'skill_001', status: 'disabled' } });
    }
    throw new Error(`Unexpected fetch call: ${String(input)}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);
  return { agentPatchBodies, skillPatchBodies };
}

describe('AI capabilities page', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('edits an existing AI role record from the list', async () => {
    const { agentPatchBodies } = installCapabilitiesFetchMock();

    render(<AiCapabilitiesPage />);

    expect(screen.queryByRole('heading', { name: 'AI 能力配置' })).not.toBeInTheDocument();
    expect(await screen.findByRole('tab', { name: 'AI角色' })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Agent 管理' })).not.toBeInTheDocument();
    expect(await screen.findByText('洞察 Agent')).toBeInTheDocument();
    expect(await screen.findByText('反馈 Agent')).toBeInTheDocument();
    expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
    expect(screen.getAllByText('默认模型网关 (gpt-4.1-mini)')).toHaveLength(2);
    const agentRow = screen.getByText('洞察 Agent').closest('tr');
    expect(agentRow).not.toBeNull();
    fireEvent.click(within(agentRow as HTMLElement).getByRole('button', { name: '编辑' }));

    const agentDialog = await screen.findByRole('dialog', { name: '编辑 AI角色' });
    expect(within(agentDialog).getByLabelText('名称')).toHaveValue('洞察 Agent');
    expect(within(agentDialog).getByLabelText('默认 Skill IDs')).toHaveValue('skill_001');
    expect(within(agentDialog).getByText('默认模型网关 / gpt-4.1-mini / 默认')).toBeInTheDocument();
    expect(within(agentDialog).getByText('启用')).toBeInTheDocument();
    fireEvent.click(within(agentDialog).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(agentPatchBodies).toEqual([
        expect.objectContaining({
          code: 'insight_agent',
          default_skill_ids: ['skill_001'],
          name: '洞察 Agent',
          status: 'active',
          system_prompt: '分析用户反馈',
        }),
      ]),
    );
  });

  it('uses the unified management list filters and saved views for AI roles', async () => {
    installCapabilitiesFetchMock();

    render(<AiCapabilitiesPage />);

    expect(await screen.findByText('洞察 Agent')).toBeInTheDocument();
    expect(screen.getByText('反馈 Agent')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('关键词'), { target: { value: 'feedback_agent' } });
    fireEvent.click(screen.getByRole('button', { name: '查询' }));

    await waitFor(() => expect(screen.queryByText('洞察 Agent')).not.toBeInTheDocument());
    expect(screen.getByText('反馈 Agent')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '保存视图' }));
    fireEvent.change(screen.getByLabelText('筛选视图名称'), {
      target: { value: '反馈角色' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存筛选视图' }));

    await waitFor(() => {
      const storedViews = JSON.parse(
        window.localStorage.getItem(
          'ai-brain:management-list-filter-views:tasks.ai-capabilities.agents',
        ) ?? '[]',
      );
      expect(storedViews).toMatchObject([
        {
          name: '反馈角色',
          query: {
            filters: {
              searchText: 'feedback_agent',
            },
          },
        },
      ]);
    });
  });

  it('normalizes object shaped model gateway references when editing an AI role', async () => {
    installCapabilitiesFetchMock();

    render(<AiCapabilitiesPage />);

    expect(await screen.findByText('反馈 Agent')).toBeInTheDocument();
    const agentRow = screen.getByText('反馈 Agent').closest('tr');
    expect(agentRow).not.toBeNull();
    fireEvent.click(within(agentRow as HTMLElement).getByRole('button', { name: '编辑' }));

    const agentDialog = await screen.findByRole('dialog', { name: '编辑 AI角色' });
    expect(within(agentDialog).getByLabelText('名称')).toHaveValue('反馈 Agent');
    expect(within(agentDialog).getByText('默认模型网关 / gpt-4.1-mini / 默认')).toBeInTheDocument();
  });

  it('edits an existing Skill record from the list', async () => {
    const { skillPatchBodies } = installCapabilitiesFetchMock();

    render(<AiCapabilitiesPage />);

    fireEvent.click(screen.getByRole('tab', { name: 'Skill 管理' }));
    expect(await screen.findByText('用户洞察采集')).toBeInTheDocument();
    const skillRow = screen.getByText('用户洞察采集').closest('tr');
    expect(skillRow).not.toBeNull();
    fireEvent.click(within(skillRow as HTMLElement).getByRole('button', { name: '编辑' }));

    const skillDialog = await screen.findByRole('dialog', { name: '编辑 Skill' });
    expect(within(skillDialog).getByLabelText('名称')).toHaveValue('用户洞察采集');
    expect(within(skillDialog).getByLabelText('Prompt 模板')).toHaveValue('采集用户反馈');
    expect(within(skillDialog).getByLabelText('输入 Schema JSON')).toHaveValue(
      JSON.stringify({ properties: { rows: { type: 'array' } }, type: 'object' }, null, 2),
    );
    expect(within(skillDialog).getByLabelText('输出 Schema JSON')).toHaveValue(
      JSON.stringify(
        {
          properties: { insights: { type: 'array' } },
          required: ['insights'],
          type: 'object',
        },
        null,
        2,
      ),
    );
    fireEvent.change(within(skillDialog).getByLabelText('输出 Schema JSON'), {
      target: {
        value: JSON.stringify(
          {
            properties: {
              insights: { type: 'array' },
              summary: { type: 'string' },
            },
            required: ['insights', 'summary'],
            type: 'object',
          },
          null,
          2,
        ),
      },
    });
    expect(within(skillDialog).getByText('启用')).toBeInTheDocument();
    fireEvent.click(within(skillDialog).getByRole('button', { name: /保\s*存/ }));

    await waitFor(() =>
      expect(skillPatchBodies).toEqual([
        expect.objectContaining({
          code: 'user_insight_collect',
          input_schema: {
            properties: { rows: { type: 'array' } },
            type: 'object',
          },
          name: '用户洞察采集',
          output_schema: {
            properties: {
              insights: { type: 'array' },
              summary: { type: 'string' },
            },
            required: ['insights', 'summary'],
            type: 'object',
          },
          prompt_template: '采集用户反馈',
          status: 'active',
          version: '1.0.0',
        }),
      ]),
    );
  });

  it('deletes an existing AI role by disabling it', async () => {
    const { agentPatchBodies } = installCapabilitiesFetchMock();

    render(<AiCapabilitiesPage />);

    expect(await screen.findByText('洞察 Agent')).toBeInTheDocument();
    const agentRow = screen.getByText('洞察 Agent').closest('tr');
    expect(agentRow).not.toBeNull();
    fireEvent.click(within(agentRow as HTMLElement).getByRole('button', { name: '删除' }));
    expect(await screen.findByText('确认删除该 AI角色？')).toBeInTheDocument();
    const agentConfirm = screen.getByText('确认删除该 AI角色？').closest('.ant-popover');
    expect(agentConfirm).not.toBeNull();
    fireEvent.click(within(agentConfirm as HTMLElement).getByRole('button', { name: /删\s*除/ }));

    await waitFor(() => expect(agentPatchBodies).toEqual([{ status: 'disabled' }]));
  });

  it('deletes an existing Skill by disabling it', async () => {
    const { skillPatchBodies } = installCapabilitiesFetchMock();

    render(<AiCapabilitiesPage />);

    fireEvent.click(screen.getByRole('tab', { name: 'Skill 管理' }));
    expect(await screen.findByText('用户洞察采集')).toBeInTheDocument();
    const skillRow = screen.getByText('用户洞察采集').closest('tr');
    expect(skillRow).not.toBeNull();
    fireEvent.click(within(skillRow as HTMLElement).getByRole('button', { name: '删除' }));
    expect(await screen.findByText('确认删除该 Skill？')).toBeInTheDocument();
    const skillConfirm = screen.getByText('确认删除该 Skill？').closest('.ant-popover');
    expect(skillConfirm).not.toBeNull();
    fireEvent.click(within(skillConfirm as HTMLElement).getByRole('button', { name: /删\s*除/ }));

    await waitFor(() => expect(skillPatchBodies).toEqual([{ status: 'disabled' }]));
  });
});
