import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  createAiAgent,
  createAiSkill,
  createScheduledJob,
  fetchAiAgents,
  fetchAiSkills,
  fetchCodeInspectionDetail,
  fetchCodeInspectionReports,
  fetchScheduledJobCatalog,
  fetchScheduledJobRuns,
  fetchScheduledJobs,
  runScheduledJob,
  updateAiAgent,
  updateAiSkill,
  uploadAiAgentPackage,
  uploadAiSkillPackage,
} from '../src/services/aiBrain';

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('scheduled AI job service mappings', () => {
  it('maps Agent, Skill and scheduled job APIs to system endpoints', async () => {
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
            items: [{ code: 'iteration_planning', id: 'skill_001', name: '迭代规划', status: 'active' }],
            total: 1,
          },
        });
      }
      if (input === '/api/system/ai-skills' && init?.method === 'POST') {
        expect(init.body).toBe(
          JSON.stringify({
            code: 'iteration_planning',
            name: '迭代规划',
            prompt_template: '生成建议',
            status: 'active',
          }),
        );
        return jsonResponse({ data: { id: 'skill_001', status: 'active' } });
      }
      if (input === '/api/system/ai-skills/skill_001' && init?.method === 'PATCH') {
        expect(init.body).toBe(JSON.stringify({ status: 'disabled' }));
        return jsonResponse({ data: { id: 'skill_001', status: 'disabled' } });
      }
      if (
        input ===
          '/api/system/ai-skills/upload?code=packaged_iteration_planning&name=%E6%96%87%E4%BB%B6%E5%8C%85%E8%BF%AD%E4%BB%A3%E8%A7%84%E5%88%92&version=1.0.0&status=active&risk_level=high&requires_human_review=true' &&
        init?.method === 'POST'
      ) {
        expect(init.headers).toMatchObject({
          Authorization: 'Bearer token-admin',
          'Content-Type': 'application/zip',
        });
        expect(init.body).toBeInstanceOf(ArrayBuffer);
        return jsonResponse({
          data: {
            code: 'packaged_iteration_planning',
            id: 'skill_package_001',
            package_checksum: 'sha256',
            source_type: 'package',
            status: 'active',
          },
        });
      }
      if (input === '/api/system/ai-agents' && init?.method === 'GET') {
        return jsonResponse({
          data: {
            items: [{ code: 'iteration_planner', id: 'agent_001', name: '迭代规划 Agent', status: 'active' }],
            total: 1,
          },
        });
      }
      if (input === '/api/system/ai-agents' && init?.method === 'POST') {
        return jsonResponse({ data: { id: 'agent_001', status: 'active' } });
      }
      if (
        input ===
          '/api/system/ai-agents/upload?brain_app_id=rd_brain&code=packaged_feedback_agent&name=%E6%96%87%E4%BB%B6%E5%8C%85%E5%8F%8D%E9%A6%88%E5%88%86%E6%9E%90%E8%A7%92%E8%89%B2&version=1.0.0&status=active&model_gateway_config_id=gateway_default&default_skill_ids=skill_001' &&
        init?.method === 'POST'
      ) {
        expect(init.headers).toMatchObject({
          Authorization: 'Bearer token-admin',
          'Content-Type': 'application/zip',
        });
        expect(init.body).toBeInstanceOf(ArrayBuffer);
        return jsonResponse({
          data: {
            code: 'packaged_feedback_agent',
            id: 'agent_package_001',
            package_checksum: 'sha256-agent',
            source_type: 'package',
            status: 'active',
          },
        });
      }
      if (input === '/api/system/ai-agents/agent_001' && init?.method === 'PATCH') {
        expect(init.body).toBe(JSON.stringify({ status: 'disabled' }));
        return jsonResponse({ data: { id: 'agent_001', status: 'disabled' } });
      }
      if (input === '/api/system/scheduled-jobs' && init?.method === 'GET') {
        return jsonResponse({
          data: {
            items: [{ id: 'scheduled_job_001', job_type: 'iteration_plan_suggestion_generate', name: '每周建议' }],
            total: 1,
          },
        });
      }
      if (input === '/api/system/scheduled-job-catalog' && init?.method === 'GET') {
        return jsonResponse({
          data: {
            code_inspection: {
              default_result_actions: [{ type: 'write_code_inspection_report' }],
              native_scan_mode: 'native_full_scan',
              scan_modes: [{ label: '本地完整扫描（clone 仓库）', value: 'native_full_scan' }],
            },
            job_types: [
              {
                label: '迭代规划建议生成',
                requires_ai_assembly: true,
                value: 'iteration_plan_suggestion_generate',
              },
            ],
            required_job_types: {
              ai_processing: ['iteration_plan_suggestion_generate'],
              plugin_resource: [],
              product: [],
            },
          },
        });
      }
      if (input === '/api/system/scheduled-jobs' && init?.method === 'POST') {
        return jsonResponse({ data: { id: 'scheduled_job_001', status: 'active' } });
      }
      if (input === '/api/system/scheduled-jobs/scheduled_job_001/run' && init?.method === 'POST') {
        return jsonResponse({ data: { id: 'scheduled_job_run_001', status: 'succeeded' } });
      }
      if (input === '/api/system/scheduled-job-runs?scheduled_job_id=scheduled_job_001' && init?.method === 'GET') {
        return jsonResponse({
          data: {
            items: [{ id: 'scheduled_job_run_001', status: 'succeeded' }],
            total: 1,
          },
        });
      }
      if (
        input ===
          '/api/system/scheduled-job-runs?status=failed&page=2&page_size=20&sort_by=finished_at&sort_order=asc'
        && init?.method === 'GET'
      ) {
        return jsonResponse({
          data: {
            items: [{ id: 'scheduled_job_run_failed', status: 'failed' }],
            page: 2,
            page_size: 20,
            performance: { duration_ms: 12, p95_target_ms: 400 },
            total: 21,
          },
        });
      }
      if (
        input === '/api/system/scheduled-job-runs?run_id=scheduled_job_run_001&run_id=scheduled_job_run_002'
        && init?.method === 'GET'
      ) {
        return jsonResponse({
          data: {
            items: [
              { id: 'scheduled_job_run_001', status: 'running' },
              { id: 'scheduled_job_run_002', status: 'queued' },
            ],
            total: 2,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchAiSkills()).resolves.toEqual([expect.objectContaining({ id: 'skill_001' })]);
    await expect(
      createAiSkill({
        code: 'iteration_planning',
        name: '迭代规划',
        prompt_template: '生成建议',
        status: 'active',
      }),
    ).resolves.toMatchObject({ id: 'skill_001' });
    await expect(updateAiSkill('skill_001', { status: 'disabled' })).resolves.toMatchObject({
      id: 'skill_001',
      status: 'disabled',
    });
    await expect(
      uploadAiSkillPackage(new File(['zip-bytes'], 'skill.zip', { type: 'application/zip' }), {
        code: 'packaged_iteration_planning',
        name: '文件包迭代规划',
        requiresHumanReview: true,
        riskLevel: 'high',
        status: 'active',
        version: '1.0.0',
      }),
    ).resolves.toMatchObject({ id: 'skill_package_001', source_type: 'package' });
    await expect(fetchAiAgents()).resolves.toEqual([expect.objectContaining({ id: 'agent_001' })]);
    await expect(createAiAgent({ code: 'iteration_planner', name: '迭代规划 Agent', system_prompt: 'x' })).resolves.toMatchObject({
      id: 'agent_001',
    });
    await expect(
      uploadAiAgentPackage(new File(['zip-bytes'], 'agent.zip', { type: 'application/zip' }), {
        code: 'packaged_feedback_agent',
        defaultSkillIds: ['skill_001'],
        modelGatewayConfigId: 'gateway_default',
        name: '文件包反馈分析角色',
        status: 'active',
        version: '1.0.0',
      }),
    ).resolves.toMatchObject({ id: 'agent_package_001', source_type: 'package' });
    await expect(updateAiAgent('agent_001', { status: 'disabled' })).resolves.toMatchObject({
      id: 'agent_001',
      status: 'disabled',
    });
    await expect(fetchScheduledJobs()).resolves.toEqual([expect.objectContaining({ id: 'scheduled_job_001' })]);
    await expect(fetchScheduledJobCatalog()).resolves.toMatchObject({
      code_inspection: {
        native_scan_mode: 'native_full_scan',
      },
      job_types: [expect.objectContaining({ value: 'iteration_plan_suggestion_generate' })],
      required_job_types: {
        ai_processing: ['iteration_plan_suggestion_generate'],
      },
    });
    await expect(
      createScheduledJob({
        job_type: 'iteration_plan_suggestion_generate',
        name: '每周建议',
        schedule_type: 'manual',
      }),
    ).resolves.toMatchObject({ id: 'scheduled_job_001' });
    await expect(runScheduledJob('scheduled_job_001')).resolves.toMatchObject({ id: 'scheduled_job_run_001' });
    await expect(fetchScheduledJobRuns({ scheduledJobId: 'scheduled_job_001' })).resolves.toEqual([
      expect.objectContaining({ id: 'scheduled_job_run_001' }),
    ]);
    await expect(
      fetchScheduledJobRuns({ runIds: ['scheduled_job_run_001', 'scheduled_job_run_002'] }),
    ).resolves.toEqual([
      expect.objectContaining({ id: 'scheduled_job_run_001' }),
      expect.objectContaining({ id: 'scheduled_job_run_002' }),
    ]);
    await expect(
      fetchScheduledJobRuns({
        page: 2,
        pageSize: 20,
        sortField: 'finished_at',
        sortOrder: 'ascend',
        status: 'failed',
      }),
    ).resolves.toMatchObject({
      page: 2,
      pageSize: 20,
      performance: { duration_ms: 12 },
      rows: [expect.objectContaining({ id: 'scheduled_job_run_failed' })],
      total: 21,
    });
  });

  it('passes code inspection result actions and reads inspection reports', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/system/scheduled-jobs' && init?.method === 'POST') {
        expect(JSON.parse(String(init.body))).toMatchObject({
          job_type: 'code_repository_inspection',
          result_actions: [
            { type: 'write_code_inspection_report' },
            { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
          ],
        });
        return jsonResponse({ data: { id: 'scheduled_job_code_001', status: 'active' } });
      }
      if (
        input ===
          '/api/governance/code-inspections?page=2&page_size=20&risk_level=critical&sort_order=desc' &&
        init?.method === 'GET'
      ) {
        return jsonResponse({
          data: {
            items: [
              {
                finding_count: 2,
                id: 'code_inspection_report_001',
                risk_level: 'critical',
                severe_finding_count: 1,
                status: 'completed',
              },
            ],
            page: 2,
            page_size: 20,
            total: 1,
          },
        });
      }
      if (input === '/api/governance/code-inspections/code_inspection_report_001' && init?.method === 'GET') {
        return jsonResponse({
          data: {
            findings: [{ id: 'code_inspection_finding_001', report_id: 'code_inspection_report_001', severity: 'critical', title: 'Hardcoded key' }],
            notifications: [],
            report: { finding_count: 1, id: 'code_inspection_report_001', risk_level: 'critical', severe_finding_count: 1, status: 'completed' },
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(
      createScheduledJob({
        job_type: 'code_repository_inspection',
        name: 'Weekly code inspection',
        result_actions: [
          { type: 'write_code_inspection_report' },
          { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
        ],
      }),
    ).resolves.toMatchObject({ id: 'scheduled_job_code_001' });
    await expect(
      fetchCodeInspectionReports({ page: 2, pageSize: 20, riskLevel: 'critical', sortOrder: 'descend' }),
    ).resolves.toMatchObject({
      page: 2,
      pageSize: 20,
      rows: [expect.objectContaining({ id: 'code_inspection_report_001' })],
      total: 1,
    });
    await expect(fetchCodeInspectionDetail('code_inspection_report_001')).resolves.toMatchObject({
      findings: [expect.objectContaining({ severity: 'critical' })],
      report: expect.objectContaining({ id: 'code_inspection_report_001' }),
    });
  });
});
