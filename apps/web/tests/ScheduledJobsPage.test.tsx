import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import ScheduledJobsPage from '../src/pages/ScheduledJobs';

function installScheduledJobsFetchMock(
  options: { jobs?: unknown[]; runResponse?: Promise<unknown>; runs?: unknown[] } = {},
) {
  const jobDeleteIds: string[] = [];
  const jobUpdateBodies: unknown[] = [];
  const jobs = options.jobs ?? [];
  const runs = options.runs ?? [];
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    if (input === '/api/system/scheduled-jobs' && init?.method === 'GET') {
      return jsonResponse({ data: { items: jobs, total: jobs.length } });
    }
    if (input === '/api/system/scheduled-jobs/scheduled_job_weekly_feedback' && init?.method === 'PATCH') {
      jobUpdateBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'scheduled_job_weekly_feedback', status: 'active' } });
    }
    if (input === '/api/system/scheduled-jobs/scheduled_job_weekly_feedback' && init?.method === 'DELETE') {
      jobDeleteIds.push('scheduled_job_weekly_feedback');
      return jsonResponse({ data: { deleted: true, id: 'scheduled_job_weekly_feedback' } });
    }
    if (input === '/api/system/scheduled-jobs/scheduled_job_weekly_feedback/run' && init?.method === 'POST') {
      const run = options.runResponse ? await options.runResponse : runs[0];
      return jsonResponse({
        data: run ?? {
          id: 'scheduled_job_run_weekly_feedback',
          records_imported: 0,
          result_summary: {},
          scheduled_job_id: 'scheduled_job_weekly_feedback',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      });
    }
    if (input === '/api/system/scheduled-job-runs' && init?.method === 'GET') {
      return jsonResponse({ data: { items: runs, total: runs.length } });
    }
    if (input === '/api/system/plugin-actions' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              action_type: 'mcp_tool',
              code: 'fetch_weekly_user_feedback',
              id: 'plugin_action_maxcompute',
              name: '获取本周用户反馈数据',
              plugin_id: 'plugin_maxcompute',
              status: 'active',
            },
          ],
          total: 1,
        },
      });
    }
    if (input === '/api/system/plugin-connections' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              environment: 'prod',
              id: 'connection_maxcompute_prod',
              name: '生产 MaxCompute 项目',
              plugin_id: 'plugin_maxcompute',
              status: 'active',
            },
          ],
          total: 1,
        },
      });
    }
    if (input === '/api/products?active_only=true&page_size=100' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [{ code: 'ai-brain', id: 'product_ai_brain', name: 'AI Brain', status: 'active' }],
          total: 1,
        },
      });
    }
    if (input === '/api/system/ai-agents' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [{ code: 'insight_agent', id: 'agent_insight', name: '洞察 Agent', status: 'active' }],
          total: 1,
        },
      });
    }
    if (input === '/api/system/ai-skills' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [{ code: 'weekly_feedback_analysis', id: 'skill_feedback', name: '每周反馈分析', status: 'active' }],
          total: 1,
        },
      });
    }
    if (input === '/api/knowledge/documents' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              content: '支付页提交后无响应时，优先排查订单幂等锁和支付回调超时。',
              doc_type: 'runbook',
              id: 'knowledge_payment_runbook',
              index_status: 'text_indexed',
              permission_roles: ['admin'],
              tags: ['支付体验'],
              title: '支付页无响应排障知识',
              updated_at: '2026-06-11T10:00:00Z',
            },
          ],
          total: 1,
        },
      });
    }
    if (input === '/api/system/model-gateway-configs' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              default_chat_model: 'scheduled-job-model',
              id: 'model_gateway_scheduled_job',
              name: '定时作业模型',
              provider: 'openai_compatible',
              status: 'active',
            },
          ],
          total: 1,
        },
      });
    }
    throw new Error(`Unexpected fetch call: ${String(input)}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);
  return { jobDeleteIds, jobUpdateBodies };
}

describe('ScheduledJobsPage', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('uses selectable references instead of requiring raw ids in the create dialog', async () => {
    installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('所属产品')).toBeInTheDocument());

    expect(within(dialog).queryByLabelText('产品 ID')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Agent ID')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Skill IDs')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('时间参数')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('连接输入参数')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('结果写入覆盖 JSON')).not.toBeInTheDocument();
    expect(within(dialog).getByLabelText('数据连接')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('AI 模型')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Agent')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Skills')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('知识引用')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('结果动作')).toBeInTheDocument();
  });

  it('can edit and delete scheduled jobs from the list', async () => {
    const { jobDeleteIds, jobUpdateBodies } = installScheduledJobsFetchMock({
      jobs: [
        {
          agent_id: 'agent_insight',
          enabled: true,
          execution_mode: 'ai_generated',
          id: 'scheduled_job_weekly_feedback',
          job_type: 'user_feedback_insight_extract',
          knowledge_document_ids: ['knowledge_payment_runbook'],
          model_gateway_config_id: 'model_gateway_scheduled_job',
          name: '每周用户反馈洞察',
          plugin_action_id: 'plugin_action_maxcompute',
          plugin_connection_id: 'connection_maxcompute_prod',
          plugin_input_mapping: {
            week_end: '{{last_full_week.end}}',
            week_start: '{{last_full_week.start}}',
          },
          plugin_output_mapping: {},
          product_id: 'product_ai_brain',
          schedule_type: 'cron',
          skill_ids: ['skill_feedback'],
          source_system: 'aliyun-maxcompute',
          status: 'active',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    expect(await screen.findByText('每周用户反馈洞察')).toBeInTheDocument();
    expect(screen.getByText('用户反馈洞察抽取（取数 + AI 分析 + 写入）')).toBeInTheDocument();
    expect(screen.getByText('生产 MaxCompute 项目 (prod)')).toBeInTheDocument();
    expect(screen.getByText('定时作业模型 (scheduled-job-model)')).toBeInTheDocument();
    expect(screen.getByText('获取本周用户反馈数据')).toBeInTheDocument();
    expect(screen.getByText('AI 生成')).toBeInTheDocument();
    expect(screen.getByText('Cron 定时')).toBeInTheDocument();
    expect(screen.getByText('启用')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: '操作' })).toHaveAttribute('data-fixed', 'right');
    fireEvent.click(screen.getByRole('button', { name: '编辑作业 每周用户反馈洞察' }));
    const dialog = await screen.findByRole('dialog', { name: '编辑定时作业' });
    expect(within(dialog).getByLabelText('名称')).toHaveValue('每周用户反馈洞察');
    expect(within(dialog).queryByDisplayValue('week_start')).not.toBeInTheDocument();
    expect(within(dialog).getByText('定时作业模型 (scheduled-job-model)')).toBeInTheDocument();
    expect(within(dialog).getByText('支付页无响应排障知识 (runbook)')).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '每周用户反馈洞察 v2' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));
    await waitFor(() =>
      expect(jobUpdateBodies).toEqual([
        expect.objectContaining({
          name: '每周用户反馈洞察 v2',
          knowledge_document_ids: ['knowledge_payment_runbook'],
          model_gateway_config_id: 'model_gateway_scheduled_job',
          plugin_input_mapping: {
            week_end: '{{last_full_week.end}}',
            week_start: '{{last_full_week.start}}',
          },
        }),
      ]),
    );

    fireEvent.click(await screen.findByRole('button', { name: '删除作业 每周用户反馈洞察' }));
    await screen.findByText('确定删除「每周用户反馈洞察」吗？');
    fireEvent.click(screen.getAllByRole('button', { name: /删\s*除/ }).at(-1)!);
    await waitFor(() => expect(jobDeleteIds).toEqual(['scheduled_job_weekly_feedback']));
  });

  it('shows scheduled job run result details', async () => {
    installScheduledJobsFetchMock({
      runs: [
        {
          collector_run_id: 'collector_run_weekly_feedback',
          config_snapshot: {
            agent_id: 'agent_insight',
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            model_gateway_config_id: 'model_gateway_scheduled_job',
            plugin_input_mapping: {
              week_end: '{{last_full_week.end}}',
              week_start: '{{last_full_week.start}}',
            },
            skill_ids: ['skill_feedback'],
          },
          finished_at: '2026-06-11T10:00:03Z',
          id: 'scheduled_job_run_weekly_feedback',
          plugin_invocation_log_id: 'plugin_invocation_log_weekly_feedback',
          records_imported: 1,
          resolved_plugin_snapshot: {
            action: { code: 'fetch_weekly_user_feedback', name: '获取本周用户反馈数据' },
          },
          resolved_agent_snapshot: {
            code: 'insight_agent',
            id: 'agent_insight',
            name: '洞察 Agent',
          },
          resolved_prompt_snapshot: {
            skill_prompt_templates: [
              {
                code: 'weekly_feedback_analysis',
                prompt_template: '提取本周用户反馈中的高价值洞察',
              },
            ],
          },
          resolved_skill_snapshots: [
            {
              code: 'weekly_feedback_analysis',
              id: 'skill_feedback',
              name: '每周反馈分析',
            },
          ],
          result_summary: {
            execution_nodes: {
              data_connection: {
                input_mapping: {
                  week_end: '20260608',
                  week_start: '20260601',
                },
                records_imported: 18,
                response_summary: {
                  json: {
                    row_count: 18,
                  },
                },
                status: 'succeeded',
              },
              result_action: {
                created_ids: ['insight_001'],
                records_imported: 1,
                status: 'succeeded',
                write_target: 'user_feedback_insights',
              },
              skill_processing: {
                model_gateway_called: true,
                model_log_id: 'model_log_weekly_feedback',
                note: '数据连接返回内容已通过平台 AI 大模型处理为结果动作可消费的结构化 JSON。',
                output: {
                  candidate_count: 1,
                  insights_created: 1,
                },
                processing_mode: 'model_gateway_json_transform',
                skill_codes: ['weekly_feedback_analysis'],
                status: 'succeeded',
              },
            },
            insight_ids: ['insight_001'],
            insights_created: 1,
            processing: {
              skill_codes: ['weekly_feedback_analysis'],
            },
            write_target: 'user_feedback_insights',
          },
          scheduled_job_id: 'scheduled_job_weekly_feedback',
          started_at: '2026-06-11T10:00:00Z',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看运行结果 scheduled_job_run_weekly_feedback' }));

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    expect(within(dialog).getByText('数据连接获取内容')).toBeInTheDocument();
    expect(within(dialog).getByText('经过 Skill 处理后的内容')).toBeInTheDocument();
    expect(within(dialog).getByText('结果动作反馈内容')).toBeInTheDocument();
    expect(within(dialog).getByText('结果摘要')).toBeInTheDocument();
    expect(dialog).toHaveTextContent('用户反馈洞察抽取（取数 + AI 分析 + 写入）');
    expect(dialog).toHaveTextContent('AI 生成');
    expect(dialog).toHaveTextContent('定时作业模型');
    expect(dialog).toHaveTextContent('洞察 Agent');
    expect(dialog).toHaveTextContent('每周反馈分析');
    expect(dialog).toHaveTextContent('row_count');
    expect(dialog).toHaveTextContent('model_log_weekly_feedback');
    expect(dialog).toHaveTextContent('model_gateway_json_transform');
    expect(dialog).toHaveTextContent('insight_001');
    expect(dialog).toHaveTextContent('weekly_feedback_analysis');
    expect(dialog).toHaveTextContent('plugin_invocation_log_weekly_feedback');
    expect(dialog).toHaveTextContent('user_feedback_insights');
  });

  it('shows an in-progress state while a scheduled job is running', async () => {
    let resolveRun!: (value: unknown) => void;
    const runResponse = new Promise<unknown>((resolve) => {
      resolveRun = resolve;
    });
    installScheduledJobsFetchMock({
      jobs: [
        {
          enabled: true,
          execution_mode: 'ai_generated',
          id: 'scheduled_job_weekly_feedback',
          job_type: 'user_feedback_insight_extract',
          name: '每周用户反馈洞察',
          plugin_action_id: 'plugin_action_maxcompute',
          plugin_connection_id: 'connection_maxcompute_prod',
          schedule_type: 'manual',
          skill_ids: ['skill_feedback'],
          status: 'active',
        },
      ],
      runResponse,
    });

    render(<ScheduledJobsPage />);

    expect(await screen.findByText('每周用户反馈洞察')).toBeInTheDocument();
    const runButton = await screen.findByRole('button', { name: '运行作业 每周用户反馈洞察' });
    fireEvent.click(runButton);

    await waitFor(() => expect(runButton).toBeDisabled());

    resolveRun({
      id: 'scheduled_job_run_weekly_feedback',
      records_imported: 36,
      result_summary: {
        execution_nodes: {
          skill_processing: {
            model_gateway_called: true,
            model_log_id: 'model_log_110',
            status: 'succeeded',
          },
        },
      },
      scheduled_job_id: 'scheduled_job_weekly_feedback',
      status: 'succeeded',
      trigger_type: 'manual',
    });

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    expect(dialog).toHaveTextContent('model_log_110');
    await waitFor(() => expect(runButton).not.toBeDisabled());
  });
});
