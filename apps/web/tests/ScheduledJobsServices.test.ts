import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  createAiAgent,
  createAiSkill,
  createScheduledJob,
  fetchAiAgents,
  fetchAiSkills,
  fetchScheduledJobRuns,
  fetchScheduledJobs,
  runScheduledJob,
  updateAiAgent,
  updateAiSkill,
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
    await expect(updateAiAgent('agent_001', { status: 'disabled' })).resolves.toMatchObject({
      id: 'agent_001',
      status: 'disabled',
    });
    await expect(fetchScheduledJobs()).resolves.toEqual([expect.objectContaining({ id: 'scheduled_job_001' })]);
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
  });
});
