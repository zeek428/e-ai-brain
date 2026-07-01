import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import ScheduledJobsPage from '../src/pages/ScheduledJobs';
import { buildScheduledJobRunDetailExportPayload } from '../src/pages/ScheduledJobs/components/ScheduledJobRunDetailModal';
import {
  ASSISTANT_DRAFT_RESOLUTION_STORAGE_KEY,
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  assistantScopedStorageKey,
  type ScheduledJobRunRecord,
} from '../src/services/aiBrain';

function installScheduledJobsFetchMock(
  options: {
    jobs?: Array<Record<string, unknown>>;
    observability?: unknown;
    resultWriteRecords?: unknown[];
    runResponse?: Promise<unknown>;
    runs?: unknown[];
  } = {},
) {
  const jobCreateBodies: unknown[] = [];
  const jobDeleteIds: string[] = [];
  const jobDryRunBodies: unknown[] = [];
  const jobListCalls: string[] = [];
  const jobUpdateBodies: unknown[] = [];
  const assistantDraftConfirmIds: string[] = [];
  const assistantDraftModificationBodies: unknown[] = [];
  const assistantDraftPatchBodies: unknown[] = [];
  const connectionTestIds: string[] = [];
  const generatedTemplateRequests: string[] = [];
  const runJobBodies: unknown[] = [];
  const runJobIds: string[] = [];
  const runListCalls: string[] = [];
  const resultWriteRecordCalls: string[] = [];
  const jobs: Array<Record<string, unknown>> = options.jobs ?? [];
  const resultWriteRecords = options.resultWriteRecords ?? [];
  const runs = options.runs ?? [];
  const observability = options.observability ?? {
    error_distribution: [],
    job_type_distribution: [],
    recent_failures: [],
    slow_runs: [],
    status_distribution: [],
    summary: {
      action_write_runs: 0,
      action_write_success_rate: 0,
      action_write_success_runs: 0,
      average_latency_ms: 0,
      average_records_imported: 0,
      cancelled_runs: 0,
      failed_runs: 0,
      failure_rate: 0,
      model_gateway_called_runs: 0,
      model_gateway_token_total: 0,
      plugin_invocation_runs: 0,
      running_runs: 0,
      success_rate: 0,
      succeeded_runs: 0,
      total_runs: 0,
    },
    trigger_type_distribution: [],
    write_target_distribution: [],
  };
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    if (
      typeof input === 'string'
      && input.startsWith('/api/system/scheduled-jobs')
      && init?.method === 'GET'
    ) {
      jobListCalls.push(input);
      return jsonResponse({ data: { items: jobs, total: jobs.length } });
    }
    if (input === '/api/system/scheduled-job-catalog' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          code_inspection: {
            builtin_rules: [
              { label: '硬编码凭据', value: 'secrets' },
              { label: '内部地址暴露', value: 'internal_addresses' },
            ],
            default_result_actions: [
              { type: 'write_code_inspection_report' },
              { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
              { severity_threshold: 'high', type: 'create_task_for_severe_findings' },
              { channels: ['email'], recipients: [], type: 'send_notification' },
            ],
            default_scan_mode: 'sync_existing_alerts',
            ignore_rules: [
              { label: 'secrets.hardcoded_credential', value: 'secrets.hardcoded_credential' },
              { label: 'metadata.internal_address_exposure', value: 'metadata.internal_address_exposure' },
            ],
            native_scan_mode: 'native_full_scan',
            result_actions: [
              { label: '写入代码巡检报告', value: 'write_code_inspection_report' },
              { label: '严重问题自动创建 Bug', value: 'create_bug_for_severe_findings' },
              { label: '严重问题自动创建整改任务', value: 'create_task_for_severe_findings' },
              { label: '发送问题消息通知', value: 'send_notification' },
            ],
            scan_modes: [
              { label: '本地完整扫描（clone 仓库）', value: 'native_full_scan' },
              { label: '同步已有告警', value: 'sync_existing_alerts' },
              { label: '触发平台扫描', value: 'trigger_platform_scan' },
            ],
            scanner_engines: [
              { label: '内置规则', value: 'builtin' },
              { label: 'gitleaks 密钥扫描', value: 'gitleaks' },
            ],
            severity_thresholds: [
              { label: 'critical', value: 'critical' },
              { label: 'high', value: 'high' },
              { label: 'medium', value: 'medium' },
            ],
          },
          connection_environments: [
            { label: '默认', value: 'default' },
            { label: '开发', value: 'dev' },
            { label: '测试', value: 'test' },
            { label: '预发', value: 'staging' },
            { label: '生产', value: 'prod' },
            { label: '沙箱', value: 'sandbox' },
          ],
          execution_modes: [
            { label: '不调用 AI', value: 'deterministic' },
            { label: 'AI 辅助', value: 'ai_assisted' },
            { label: 'AI 生成', value: 'ai_generated' },
          ],
          job_types: [
            {
              allow_create: true,
              label: '代码仓库巡检（质量 / 安全 / 规范）',
              requires_plugin_resource: true,
              requires_product: true,
              runnable: true,
              value: 'code_repository_inspection',
            },
            {
              allow_create: true,
              label: '用户反馈洞察抽取（取数 + AI 分析 + 写入）',
              requires_ai_assembly: true,
              requires_plugin_resource: true,
              requires_product: true,
              runnable: true,
              value: 'user_feedback_insight_extract',
            },
            {
              allow_create: true,
              label: '迭代规划建议生成',
              requires_ai_assembly: true,
              runnable: true,
              value: 'iteration_plan_suggestion_generate',
            },
            {
              allow_create: false,
              label: '线上日志 AI 分析',
              requires_ai_assembly: true,
              runnable: false,
              unavailable_reason: '运行处理器尚未闭环，后续通过线上日志模板补齐后开放。',
              value: 'online_log_ai_analysis',
            },
            {
              allow_create: true,
              label: '插件执行调用',
              requires_plugin_resource: true,
              runnable: true,
              value: 'plugin_action_invoke',
            },
          ],
          required_job_types: {
            ai_processing: [
              'iteration_plan_suggestion_generate',
              'online_log_ai_analysis',
              'user_feedback_insight_extract',
            ],
            plugin_resource: ['code_repository_inspection', 'plugin_action_invoke', 'user_feedback_insight_extract'],
            product: ['code_repository_inspection', 'user_feedback_insight_extract'],
          },
          schedule_types: [
            { label: '手动触发', value: 'manual' },
            { label: 'Cron 定时', value: 'cron' },
            { label: '固定间隔', value: 'interval' },
          ],
        },
      });
    }
    if (input === '/api/system/scheduled-job-templates' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              code: 'weekly_feedback_insight',
              name: '每周用户反馈洞察抽取',
              payload_defaults: {
                cron_expression: '0 9 * * MON',
                enabled: true,
                execution_mode: 'ai_generated',
                job_type: 'user_feedback_insight_extract',
                name: '每周用户反馈洞察抽取',
                plugin_input_mapping: {
                  week_end: '{{last_full_week.end}}',
                  week_start: '{{last_full_week.start}}',
                },
                result_actions: [],
                schedule_type: 'cron',
                source_system: 'aliyun-maxcompute',
              },
              resource_selectors: {
                plugin_action: { code_candidates: ['fetch_weekly_user_feedback'] },
              },
              template_version: 'v1',
              wizard_steps: [
                { key: 'data_connection', required: true, title: '数据连接' },
                { key: 'ai_processing', required: true, title: 'AI 处理' },
                { key: 'knowledge_reference', required: false, title: '知识引用' },
                { key: 'result_write', required: true, title: '结果写入' },
                { key: 'schedule', required: true, title: '调度' },
              ],
            },
            {
              code: 'code_repository_inspection',
              name: '代码仓库质量 / 安全 / 规范巡检',
              payload_defaults: {
                cron_expression: '0 2 * * MON',
                enabled: true,
                execution_mode: 'deterministic',
                job_type: 'code_repository_inspection',
                knowledge_document_ids: [],
                name: '代码仓库质量安全规范巡检',
                result_actions: [
                  { type: 'write_code_inspection_report' },
                  { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
                  { severity_threshold: 'high', type: 'create_task_for_severe_findings' },
                  { channels: ['email'], recipients: [], type: 'send_notification' },
                ],
                schedule_type: 'cron',
                skill_ids: [],
                source_system: 'code-inspection',
              },
              resource_selectors: {
                plugin_action: {
                  code_candidates: ['scan_github_code_inspection', 'scan_gitlab_code_inspection'],
                  text_candidates: ['code_inspection', '代码巡检'],
                },
              },
              template_version: 'v1',
              wizard_steps: [
                { key: 'data_connection', required: true, title: '数据连接' },
                { key: 'ai_processing', required: false, title: 'AI 处理' },
                { key: 'knowledge_reference', required: false, title: '知识引用' },
                { key: 'result_write', required: true, title: '结果写入' },
                { key: 'schedule', required: true, title: '调度' },
              ],
            },
            {
              code: 'email_digest',
              name: '邮件摘要收取',
              payload_defaults: {
                enabled: true,
                execution_mode: 'ai_assisted',
                job_type: 'plugin_action_invoke',
                name: '每日邮件摘要收取',
                result_actions: [],
                schedule_type: 'cron',
                source_system: 'email',
              },
              resource_selectors: {
                plugin_action: { code_candidates: ['receive_email_messages'] },
              },
              template_version: 'v1',
              wizard_steps: [
                { key: 'data_connection', required: true, title: '数据连接' },
                { key: 'ai_processing', required: false, title: 'AI 处理' },
                { key: 'result_write', required: true, title: '结果写入' },
                { key: 'schedule', required: true, title: '调度' },
              ],
            },
            {
              code: 'gitlab_mr_review',
              name: 'GitLab MR AI 审查',
              payload_defaults: {
                enabled: true,
                execution_mode: 'ai_assisted',
                job_type: 'code_repository_inspection',
                name: 'GitLab MR AI 审查',
                result_actions: [
                  { type: 'write_code_inspection_report' },
                  { severity_threshold: 'high', type: 'create_task_for_severe_findings' },
                ],
                schedule_type: 'manual',
                source_system: 'gitlab',
              },
              resource_selectors: {
                plugin_action: { code_candidates: ['scan_gitlab_code_inspection'] },
              },
              template_version: 'v1',
              wizard_steps: [
                { key: 'data_connection', required: true, title: '数据连接' },
                { key: 'ai_processing', required: true, title: 'AI 处理' },
                { key: 'result_write', required: true, title: '结果写入' },
                { key: 'schedule', required: true, title: '调度' },
              ],
            },
            {
              code: 'ai_executor_repository_task',
              description: '默认使用系统默认 AI 大模型执行仓库任务，也可切换到本地 Runner。',
              name: 'AI 执行器仓库任务',
              payload_defaults: {
                config_json: {
                  ai_executor: {
                    executor_type: 'model_gateway',
                    runner_id: 'ai_executor_runner_system_default',
                    runner_label: '系统默认执行器',
                  },
                },
                cron_expression: '0 3 * * MON',
                enabled: true,
                execution_mode: 'deterministic',
                job_type: 'plugin_action_invoke',
                name: 'AI 执行器仓库巡检',
                result_actions: [],
                schedule_type: 'cron',
                source_system: 'ai_executor',
              },
              recommended_scenarios: ['系统默认执行器', '系统 AI 大模型仓库分析', '本地 Codex/OpenClaw Runner'],
              resource_selectors: {
                plugin_action: { code_candidates: ['run_ai_executor_instruction'] },
              },
              template_version: 'v1',
              wizard_steps: [
                { key: 'data_connection', required: true, title: '数据连接' },
                { key: 'ai_processing', required: false, title: 'AI 处理' },
                { key: 'result_write', required: true, title: '结果写入' },
                { key: 'schedule', required: true, title: '调度' },
              ],
            },
          ],
          total: 5,
        },
      });
    }
    if (input === '/api/system/scheduled-jobs' && init?.method === 'POST') {
      const body = JSON.parse(String(init.body));
      jobCreateBodies.push(body);
      return jsonResponse({ data: { id: `scheduled_job_${jobCreateBodies.length}`, ...body, status: 'active' } });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/assistant/action-drafts/')
      && !input.endsWith('/confirm')
      && !input.endsWith('/modification')
      && init?.method === 'PATCH'
    ) {
      const body = JSON.parse(String(init.body));
      assistantDraftPatchBodies.push(body);
      return jsonResponse({
        data: {
          action: 'create_scheduled_job',
          id: input.split('/').at(-1),
          metadata_json: {
            modified_fields: body.modified_fields ?? [],
            user_modified: Boolean((body.modified_fields ?? []).length),
          },
          payload: body.payload,
          risk_level: 'medium',
          status: 'pending',
          title: 'AI 助手草案',
        },
      });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/assistant/action-drafts/')
      && input.endsWith('/confirm')
      && init?.method === 'POST'
    ) {
      const draftId = input.split('/').at(-2) ?? '';
      assistantDraftConfirmIds.push(draftId);
      return jsonResponse({
        data: {
          draft: {
            action: 'create_scheduled_job',
            id: draftId,
            payload: {},
            status: 'confirmed',
            title: 'AI 助手草案',
          },
          run: {
            action: 'create_scheduled_job',
            draft_id: draftId,
            id: `assistant_action_run_${assistantDraftConfirmIds.length}`,
            result: {
              id: `scheduled_job_from_draft_${assistantDraftConfirmIds.length}`,
              name: '表单确认后的定时作业',
            },
            result_id: `scheduled_job_from_draft_${assistantDraftConfirmIds.length}`,
            result_type: 'scheduled_job',
            status: 'succeeded',
          },
        },
      });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/assistant/action-drafts/')
      && input.endsWith('/modification')
      && init?.method === 'POST'
    ) {
      const body = JSON.parse(String(init.body));
      assistantDraftModificationBodies.push(body);
      return jsonResponse({
        data: {
          action: 'create_scheduled_job',
          id: input.split('/').at(-2),
          metadata_json: body,
          payload: {},
          risk_level: 'medium',
          status: 'pending',
          title: 'AI 助手草案',
        },
      });
    }
    if (input === '/api/system/scheduled-jobs/dry-run' && init?.method === 'POST') {
      const body = JSON.parse(String(init.body));
      jobDryRunBodies.push(body);
      return jsonResponse({
        data: {
          job_type: body.job_type,
          stages: {
            ai_processing: {
              mapping_status: 'succeeded',
              output_schema: { required: ['insights'], type: 'object' },
              will_call_model_gateway: true,
            },
            data_connection: {
              connection_id: 'connection_maxcompute_prod',
              records_imported: 18,
              request_url: 'https://maxcompute.example.com/api?week_start=20260601',
              status: 'succeeded',
            },
            result_actions: [
              {
                action_id: 'plugin_action_maxcompute',
                write_preview: { records_imported: 18, write_target_label: '用户洞察表' },
                write_target: 'user_feedback_insights',
              },
            ],
          },
          status: 'succeeded',
        },
      });
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
      runJobIds.push('scheduled_job_weekly_feedback');
      runJobBodies.push(JSON.parse(String(init.body ?? '{}')));
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
    if (
      input === '/api/system/scheduled-job-runs/scheduled_job_run_weekly_feedback/template'
      && init?.method === 'POST'
    ) {
      generatedTemplateRequests.push('scheduled_job_run_weekly_feedback');
      return jsonResponse({
        data: {
          code: 'generated_from_scheduled_job_run_weekly_feedback',
          name: '每周反馈运行模板',
          payload_defaults: {
            config_json: {
              template_source: {
                source_id: 'scheduled_job_run_weekly_feedback',
                source_type: 'scheduled_job_run',
                title: '每周反馈运行模板',
              },
            },
            cron_expression: '0 9 * * MON',
            enabled: true,
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            name: '每周反馈运行模板',
            plugin_action_id: 'plugin_action_maxcompute',
            plugin_connection_id: 'connection_maxcompute_prod',
            schedule_type: 'cron',
            skill_ids: ['skill_feedback'],
            source_system: 'aliyun-maxcompute',
          },
          source_run_id: 'scheduled_job_run_weekly_feedback',
          template_version: 'generated-v1',
          wizard_steps: [
            { key: 'data_connection', required: true, title: '数据连接' },
            { key: 'ai_processing', required: true, title: 'AI 处理' },
            { key: 'result_write', required: true, title: '结果写入' },
            { key: 'schedule', required: true, title: '调度' },
          ],
        },
      });
    }
    if (input === '/api/system/scheduled-job-runs/observability' && init?.method === 'GET') {
      return jsonResponse({ data: observability });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/system/scheduled-job-runs')
      && init?.method === 'GET'
    ) {
      runListCalls.push(input);
      return jsonResponse({ data: { items: runs, total: runs.length } });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/system/scheduled-jobs/')
      && init?.method === 'PATCH'
    ) {
      const jobId = input.split('/').at(-1);
      const body = JSON.parse(String(init.body ?? '{}'));
      jobUpdateBodies.push(body);
      const existingJob = jobs.find((item) => item.id === jobId) ?? { id: jobId };
      return jsonResponse({ data: { ...existingJob, ...body, id: jobId } });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/system/result-write-records')
      && init?.method === 'GET'
    ) {
      resultWriteRecordCalls.push(input);
      return jsonResponse({ data: { items: resultWriteRecords, total: resultWriteRecords.length } });
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
            {
              action_type: 'http_request',
              code: 'write_weekly_user_feedback_insights',
              id: 'plugin_action_feedback_write',
              name: '写入用户洞察表',
              plugin_id: 'plugin_maxcompute',
              status: 'active',
            },
            {
              action_type: 'http_request',
              code: 'scan_github_code_inspection',
              id: 'plugin_action_github_scan',
              name: 'GitHub 代码巡检',
              plugin_id: 'plugin_github',
              status: 'active',
            },
            {
              action_type: 'http_request',
              code: 'scan_gitlab_code_inspection',
              id: 'plugin_action_gitlab_scan',
              name: 'GitLab 代码巡检',
              plugin_id: 'plugin_gitlab',
              status: 'active',
            },
            {
              action_type: 'mcp_tool',
              code: 'run_ai_executor_instruction',
              id: 'plugin_action_ai_executor_command',
              name: 'AI 执行器下达指令',
              plugin_id: 'plugin_standard_ai_executor',
              status: 'active',
            },
          ],
          total: 4,
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
            {
              environment: 'prod',
              id: 'connection_maxcompute_backup',
              name: '备用 MaxCompute 项目',
              plugin_id: 'plugin_maxcompute',
              status: 'active',
            },
            {
              environment: 'test',
              id: 'connection_maxcompute_test',
              name: '测试 MaxCompute 项目',
              plugin_id: 'plugin_maxcompute',
              status: 'active',
            },
            {
              environment: 'prod',
              id: 'connection_github_prod',
              name: '生产 GitHub 组织',
              plugin_id: 'plugin_github',
              status: 'active',
            },
            {
              environment: 'prod',
              id: 'connection_gitlab_prod',
              name: '生产 GitLab 项目',
              plugin_id: 'plugin_gitlab',
              status: 'active',
            },
            {
              environment: 'default',
              id: 'connection_ai_executor_system',
              name: '系统默认 AI 执行器',
              plugin_id: 'plugin_standard_ai_executor',
              status: 'active',
            },
          ],
          total: 4,
        },
      });
    }
    if (
      input === '/api/system/plugin-connections/connection_maxcompute_prod/test'
      && init?.method === 'POST'
    ) {
      connectionTestIds.push('connection_maxcompute_prod');
      return jsonResponse({
        data: {
          checks: [
            { name: 'endpoint_configured', status: 'succeeded' },
            { name: 'network_request', status: 'succeeded' },
          ],
          latency_ms: 128,
          request_summary: {
            method: 'GET',
            url: 'https://maxcompute.example.com/api?week_start=20260601',
          },
          status: 'succeeded',
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
    if (input === '/api/products/product_ai_brain/git-repositories?active_only=true' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              default_branch: 'main',
              git_provider: 'gitlab',
              id: 'repo_zqf',
              name: '醉清风APP',
              project_path: 'zqf-play-app/intofun',
              status: 'active',
            },
          ],
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
  return {
    assistantDraftConfirmIds,
    assistantDraftModificationBodies,
    assistantDraftPatchBodies,
    connectionTestIds,
    generatedTemplateRequests,
    jobCreateBodies,
    jobDeleteIds,
    jobDryRunBodies,
    jobListCalls,
    jobUpdateBodies,
    resultWriteRecordCalls,
    runJobBodies,
    runJobIds,
    runListCalls,
  };
}

describe('ScheduledJobsPage', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.history.pushState({}, '', '/');
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('loads scheduled job tables through server-side pagination', async () => {
    const { jobListCalls, runListCalls } = installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    await waitFor(() =>
      expect(jobListCalls).toContain(
        '/api/system/scheduled-jobs?page=1&page_size=10&sort_by=next_run_at&sort_order=desc',
      ),
    );
    await waitFor(() =>
      expect(runListCalls).toContain(
        '/api/system/scheduled-job-runs?page=1&page_size=10&sort_by=started_at&sort_order=desc',
      ),
    );
  });

  it('uses selectable references instead of requiring raw ids in the create dialog', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);
    installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    expect(screen.queryByRole('heading', { name: '定时作业' })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('所属产品')).toBeInTheDocument());

    expect(within(dialog).queryByLabelText('产品 ID')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Agent ID')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Agent')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('Skill IDs')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('时间参数')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('连接输入参数')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('结果写入覆盖 JSON')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('来源系统')).not.toBeInTheDocument();
    const scheduleGroup = within(dialog).getByLabelText('调度配置');
    expect(within(scheduleGroup).getByLabelText('调度方式')).toBeInTheDocument();
    expect(within(scheduleGroup).getByLabelText('Cron 表达式')).toBeInTheDocument();
    expect(within(scheduleGroup).getByLabelText('间隔秒数')).toBeInTheDocument();
    expect(within(scheduleGroup).getByLabelText('调度方式').compareDocumentPosition(
      within(scheduleGroup).getByLabelText('Cron 表达式'),
    ) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(scheduleGroup).getByLabelText('Cron 表达式').compareDocumentPosition(
      within(scheduleGroup).getByLabelText('间隔秒数'),
    ) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(within(dialog).queryByLabelText('连接环境')).not.toBeInTheDocument();
    expect(within(dialog).getByLabelText('数据连接')).toBeInTheDocument();
    expect(within(dialog).getByText('可选择多个连接，运行时按配置顺序作为数据来源')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('执行链路')).toHaveTextContent('数据连接 → AI执行 → 动作 → 运行记录');
    expect(within(dialog).getByLabelText('数据连接配置')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('AI执行配置')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('AI执行')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('AI 模型')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('AI角色')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Skills')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('知识引用')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('动作配置')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('写入策略')).toBeInTheDocument();
    expect(within(dialog).getByText('选择结果写到哪里或通知到哪里，后台按配置顺序执行对应动作')).toBeInTheDocument();
    expect(within(dialog).queryByText('数据扫描执行')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('结果写入执行')).not.toBeInTheDocument();
    expect(consoleError).not.toHaveBeenCalled();
  });

  it('exposes native code inspection rule configuration in the create dialog', async () => {
    installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('作业模板')).toBeInTheDocument());
    fireEvent.mouseDown(within(dialog).getByLabelText('作业模板'));
    fireEvent.click(await screen.findByText('代码仓库质量 / 安全 / 规范巡检'));

    await waitFor(() => expect(within(dialog).getByLabelText('代码仓库')).toBeInTheDocument());
    expect(within(dialog).getByLabelText('批量代码仓库')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('扫描引擎')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('内置规则')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('严重级别阈值')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('忽略目录')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('忽略规则')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Baseline Fingerprints')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('已接受风险 Fingerprints')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('启用质量门禁')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Critical 上限')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('High 上限')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Medium 上限')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('增量基线 Commit')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('异步执行')).toBeInTheDocument();
  });

  it('shows scheduled job run observability before the run list', async () => {
    installScheduledJobsFetchMock({
      observability: {
        error_distribution: [{ count: 1, error: 'MODEL_GATEWAY_FAILED' }],
        job_type_distribution: [{ count: 2, job_type: 'user_feedback_insight_extract' }],
        recent_failures: [
          {
            error_code: 'MODEL_GATEWAY_FAILED',
            error_message: '模型处理失败',
            id: 'scheduled_job_run_failed',
            job_name: '每周反馈洞察',
          },
        ],
        slow_runs: [
          {
            id: 'scheduled_job_run_slow',
            job_name: '代码巡检',
            latency_ms: 5000,
            records_imported: 3,
            status: 'succeeded',
          },
        ],
        status_distribution: [
          { count: 1, status: 'succeeded' },
          { count: 1, status: 'failed' },
        ],
        summary: {
          action_write_runs: 2,
          action_write_success_rate: 50,
          action_write_success_runs: 1,
          average_latency_ms: 2500,
          average_records_imported: 1.5,
          cancelled_runs: 0,
          failed_runs: 1,
          failure_rate: 50,
          model_gateway_called_runs: 1,
          model_gateway_token_total: 42,
          plugin_invocation_runs: 2,
          running_runs: 0,
          success_rate: 50,
          succeeded_runs: 1,
          total_runs: 2,
        },
        trigger_type_distribution: [{ count: 2, trigger_type: 'manual' }],
        write_target_distribution: [{ count: 1, write_target: 'user_feedback_insights' }],
      },
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));

    expect(await screen.findByText('运行健康概览')).toBeInTheDocument();
    expect(screen.getByText('总运行数')).toBeInTheDocument();
    expect(screen.getByText('AI 调用次数')).toBeInTheDocument();
    expect(screen.getByText('Token 总量')).toBeInTheDocument();
    expect(screen.getByText('结果写入成功率')).toBeInTheDocument();
    expect(screen.getAllByText('MODEL_GATEWAY_FAILED').length).toBeGreaterThan(0);
    expect(screen.getByText('模型处理失败')).toBeInTheDocument();
    expect(screen.getByText('scheduled_job_run_slow')).toBeInTheDocument();
    expect(screen.getByText('5000')).toBeInTheDocument();
  });

  it('shows an orchestration flow with status preview and a data connection test', async () => {
    const { connectionTestIds } = installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByText('执行链路')).toBeInTheDocument());
    expect(within(dialog).getByText('执行链路：数据连接 → AI执行 → 动作 → 运行记录')).toBeInTheDocument();

    expect(within(dialog).getByLabelText('编排节点 数据连接')).toHaveTextContent('待配置');
    expect(within(dialog).getByLabelText('编排节点 AI执行')).toHaveTextContent('待配置');
    expect(within(dialog).getByLabelText('编排节点 知识引用')).toHaveTextContent('可选');
    expect(within(dialog).getByLabelText('编排节点 动作')).toHaveTextContent('待配置');

    fireEvent.mouseDown(within(dialog).getByLabelText('作业模板'));
    expect(await screen.findByText('邮件摘要收取')).toBeInTheDocument();
    expect(screen.getByText('GitLab MR AI 审查')).toBeInTheDocument();
    expect(screen.getByText('AI 执行器仓库任务')).toBeInTheDocument();
    fireEvent.click(await screen.findByText('每周用户反馈洞察抽取'));

    await waitFor(() =>
      expect(within(dialog).getByLabelText('编排节点 数据连接')).toHaveTextContent('已配置'),
    );
    expect(within(dialog).getByLabelText('编排节点 数据连接')).toHaveTextContent('生产 MaxCompute 项目');
    expect(within(dialog).getByLabelText('编排节点 AI执行')).toHaveTextContent('已配置');
    expect(within(dialog).getByLabelText('编排节点 AI执行')).toHaveTextContent('定时作业模型');
    expect(within(dialog).getByLabelText('编排节点 知识引用')).toHaveTextContent('已选择');
    expect(within(dialog).getByLabelText('编排节点 动作')).toHaveTextContent('已配置');
    expect(within(dialog).getByLabelText('编排节点 动作')).toHaveTextContent('获取本周用户反馈数据');

    fireEvent.click(within(dialog).getByRole('button', { name: '测试数据连接' }));

    await waitFor(() => expect(connectionTestIds).toEqual(['connection_maxcompute_prod']));
    expect(within(dialog).getByLabelText('编排节点 数据连接')).toHaveTextContent('连接测试 succeeded');
    expect(within(dialog).getByLabelText('编排节点 数据连接')).toHaveTextContent('128ms');
  });

  it('runs a full scheduled job draft dry-run from the create dialog', async () => {
    const { jobDryRunBodies } = installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('作业模板')).toBeInTheDocument());
    fireEvent.mouseDown(within(dialog).getByLabelText('作业模板'));
    fireEvent.click(await screen.findByText('每周用户反馈洞察抽取'));

    fireEvent.click(within(dialog).getByRole('button', { name: '全链路试运行' }));

    await waitFor(() =>
      expect(jobDryRunBodies[0]).toMatchObject({
        agent_id: 'agent_insight',
        job_type: 'user_feedback_insight_extract',
        model_gateway_config_id: 'model_gateway_scheduled_job',
        plugin_action_id: 'plugin_action_maxcompute',
        plugin_connection_id: 'connection_maxcompute_prod',
        skill_ids: ['skill_feedback'],
      }),
    );
    const dryRunResult = await within(dialog).findByLabelText('全链路试运行结果');
    expect(within(dryRunResult).getByText('数据连接预览')).toBeInTheDocument();
    expect(within(dryRunResult).getByText('AI契约校验')).toBeInTheDocument();
    expect(within(dryRunResult).getByText('结果写入预览')).toBeInTheDocument();
    expect(within(dryRunResult).getByText(/connection_maxcompute_prod/)).toBeInTheDocument();
    expect(within(dryRunResult).getByText(/user_feedback_insights/)).toBeInTheDocument();
  });

  it('shows data connection options by name without submitting environment metadata', async () => {
    const { jobCreateBodies } = installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    fireEvent.mouseDown(within(dialog).getByLabelText('数据连接'));

    expect(await screen.findByText('测试 MaxCompute 项目')).toBeInTheDocument();
    expect(screen.getByText('生产 MaxCompute 项目')).toBeInTheDocument();
    expect(screen.queryByText('生产 MaxCompute 项目 (prod)')).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('作业模板'));
    fireEvent.click(await screen.findByText('每周用户反馈洞察抽取'));
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() => {
      expect(jobCreateBodies[0]).toMatchObject({
        plugin_connection_id: 'connection_maxcompute_prod',
      });
      expect(jobCreateBodies[0]).not.toHaveProperty('connection_environment');
    });
  });

  it('creates scheduled jobs from scene templates', async () => {
    const { jobCreateBodies } = installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const feedbackDialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(feedbackDialog).getByLabelText('作业模板')).toBeInTheDocument());
    fireEvent.mouseDown(within(feedbackDialog).getByLabelText('作业模板'));
    fireEvent.click(await screen.findByText('每周用户反馈洞察抽取'));

    expect(within(feedbackDialog).getByLabelText('名称')).toHaveValue('每周用户反馈洞察抽取');
    expect(within(feedbackDialog).getByText('AI Brain (ai-brain)')).toBeInTheDocument();
    expect(within(feedbackDialog).getByText('生产 MaxCompute 项目')).toBeInTheDocument();
    expect(within(feedbackDialog).getByText('定时作业模型 (scheduled-job-model)')).toBeInTheDocument();
    expect(within(feedbackDialog).getByText('洞察 Agent (insight_agent)')).toBeInTheDocument();
    expect(within(feedbackDialog).getByText('每周反馈分析 (weekly_feedback_analysis)')).toBeInTheDocument();
    expect(within(feedbackDialog).getByText('支付页无响应排障知识 (runbook)')).toBeInTheDocument();
    expect(within(feedbackDialog).getByText('获取本周用户反馈数据')).toBeInTheDocument();
    expect(within(feedbackDialog).getByDisplayValue('0 9 * * MON')).toBeInTheDocument();
    expect(within(feedbackDialog).getByDisplayValue('aliyun-maxcompute')).toBeInTheDocument();

    fireEvent.mouseDown(within(feedbackDialog).getByLabelText('数据连接'));
    fireEvent.click(await screen.findByText('备用 MaxCompute 项目'));
    fireEvent.mouseDown(within(feedbackDialog).getByLabelText('写入策略'));
    fireEvent.click(await screen.findByText('写入用户洞察表'));

    fireEvent.click(within(feedbackDialog).getByRole('button', { name: /OK|确\s*定/ }));
    await waitFor(() =>
      expect(jobCreateBodies[0]).toMatchObject({
        agent_id: 'agent_insight',
        config_json: {},
        cron_expression: '0 9 * * MON',
        enabled: true,
        execution_mode: 'ai_generated',
        job_type: 'user_feedback_insight_extract',
        knowledge_document_ids: ['knowledge_payment_runbook'],
        model_gateway_config_id: 'model_gateway_scheduled_job',
        name: '每周用户反馈洞察抽取',
        plugin_action_id: 'plugin_action_maxcompute',
        plugin_action_ids: ['plugin_action_maxcompute', 'plugin_action_feedback_write'],
        plugin_connection_id: 'connection_maxcompute_prod',
        plugin_connection_ids: ['connection_maxcompute_prod', 'connection_maxcompute_backup'],
        plugin_input_mapping: {
          week_end: '{{last_full_week.end}}',
          week_start: '{{last_full_week.start}}',
        },
        product_id: 'product_ai_brain',
        schedule_type: 'cron',
        skill_ids: ['skill_feedback'],
        source_system: 'aliyun-maxcompute',
      }),
    );
    expect(jobCreateBodies[0]).not.toHaveProperty('connection_environment');

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const codeDialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(codeDialog).getByLabelText('作业模板')).toBeInTheDocument());
    fireEvent.mouseDown(within(codeDialog).getByLabelText('作业模板'));
    fireEvent.click(await screen.findByText('代码仓库质量 / 安全 / 规范巡检'));

    expect(within(codeDialog).getByLabelText('名称')).toHaveValue('代码仓库质量安全规范巡检');
    expect(within(codeDialog).getByText('生产 GitHub 组织')).toBeInTheDocument();
    expect(within(codeDialog).getByText('GitHub 代码巡检')).toBeInTheDocument();
    expect(within(codeDialog).getByDisplayValue('0 2 * * MON')).toBeInTheDocument();
    expect(within(codeDialog).getByDisplayValue('code-inspection')).toBeInTheDocument();

    fireEvent.click(within(codeDialog).getByRole('button', { name: /OK|确\s*定/ }));
    await waitFor(() =>
      expect(jobCreateBodies[1]).toMatchObject({
        cron_expression: '0 2 * * MON',
        enabled: true,
        execution_mode: 'deterministic',
        job_type: 'code_repository_inspection',
        name: '代码仓库质量安全规范巡检',
        plugin_action_id: 'plugin_action_github_scan',
        plugin_connection_id: 'connection_github_prod',
        product_id: 'product_ai_brain',
        result_actions: [
          { type: 'write_code_inspection_report' },
          { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
          { severity_threshold: 'high', type: 'create_task_for_severe_findings' },
          { channels: ['email'], recipients: [], type: 'send_notification' },
        ],
        schedule_type: 'cron',
        source_system: 'code-inspection',
      }),
    );
    expect(jobCreateBodies[1]).not.toHaveProperty('connection_environment');

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const executorDialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(executorDialog).getByLabelText('作业模板')).toBeInTheDocument());
    fireEvent.mouseDown(within(executorDialog).getByLabelText('作业模板'));
    fireEvent.click(await screen.findByText('AI 执行器仓库任务'));

    expect(within(executorDialog).getByLabelText('名称')).toHaveValue('AI 执行器仓库巡检');
    expect(within(executorDialog).getByText('系统默认 AI 执行器')).toBeInTheDocument();
    expect(within(executorDialog).getByText('AI 执行器下达指令')).toBeInTheDocument();
    expect(within(executorDialog).getByDisplayValue('0 3 * * MON')).toBeInTheDocument();
    expect(within(executorDialog).getByDisplayValue('ai_executor')).toBeInTheDocument();

    fireEvent.click(within(executorDialog).getByRole('button', { name: /OK|确\s*定/ }));
    await waitFor(() =>
      expect(jobCreateBodies[2]).toMatchObject({
        config_json: {
          ai_executor: {
            executor_type: 'model_gateway',
            runner_id: 'ai_executor_runner_system_default',
            runner_label: '系统默认执行器',
          },
        },
        cron_expression: '0 3 * * MON',
        enabled: true,
        execution_mode: 'deterministic',
        job_type: 'plugin_action_invoke',
        name: 'AI 执行器仓库巡检',
        plugin_action_id: 'plugin_action_ai_executor_command',
        plugin_connection_id: 'connection_ai_executor_system',
        product_id: 'product_ai_brain',
        schedule_type: 'cron',
        source_system: 'ai_executor',
      }),
    );
    expect(jobCreateBodies[2]).not.toHaveProperty('connection_environment');
  }, 15000);

  it('opens the create dialog from an assistant scheduled job draft and confirms through the server draft', async () => {
    const { assistantDraftConfirmIds, assistantDraftPatchBodies, jobCreateBodies } = installScheduledJobsFetchMock();
    window.sessionStorage.setItem(
      assistantScopedStorageKey(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY),
      JSON.stringify({
        draftId: 'assistant_draft_weekly_feedback_insight',
        payload: {
          agent_id: 'agent_insight',
          cron_expression: '0 9 * * MON',
          enabled: true,
          execution_mode: 'ai_generated',
          job_type: 'user_feedback_insight_extract',
          knowledge_document_ids: ['knowledge_payment_runbook'],
          model_gateway_config_id: 'model_gateway_scheduled_job',
          name: '每周用户反馈洞察抽取',
          plugin_action_id: 'plugin_action_maxcompute',
          plugin_connection_id: 'connection_maxcompute_prod',
          plugin_input_mapping: {
            week_end: '{{last_full_week.end}}',
            week_start: '{{last_full_week.start}}',
          },
          product_id: 'product_ai_brain',
          schedule_type: 'cron',
          skill_ids: ['skill_feedback'],
          source_system: 'aliyun-maxcompute',
        },
        title: '每周用户反馈洞察抽取',
      }),
    );

    render(<ScheduledJobsPage />);

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    expect(within(dialog).getByLabelText('名称')).toHaveValue('每周用户反馈洞察抽取');
    expect(within(dialog).getByText('生产 MaxCompute 项目')).toBeInTheDocument();
    expect(within(dialog).getByText('洞察 Agent (insight_agent)')).toBeInTheDocument();
    expect(within(dialog).getByText('每周反馈分析 (weekly_feedback_analysis)')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('0 9 * * MON')).toBeInTheDocument();
    expect(window.sessionStorage.getItem(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY)).toBeNull();

    fireEvent.change(within(dialog).getByLabelText('名称'), {
      target: { value: '每周用户反馈洞察抽取 - 人工调整' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(assistantDraftPatchBodies).toEqual([
        {
          modified_fields: ['name'],
          payload: expect.objectContaining({
            agent_id: 'agent_insight',
            config_json: expect.objectContaining({
              assistant_draft: {
                draft_id: 'assistant_draft_weekly_feedback_insight',
                source: 'assistant.action_draft',
                title: '每周用户反馈洞察抽取',
              },
            }),
            cron_expression: '0 9 * * MON',
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            knowledge_document_ids: ['knowledge_payment_runbook'],
            model_gateway_config_id: 'model_gateway_scheduled_job',
            name: '每周用户反馈洞察抽取 - 人工调整',
            plugin_action_id: 'plugin_action_maxcompute',
            plugin_connection_id: 'connection_maxcompute_prod',
            plugin_input_mapping: {
              week_end: '{{last_full_week.end}}',
              week_start: '{{last_full_week.start}}',
            },
            product_id: 'product_ai_brain',
            schedule_type: 'cron',
            skill_ids: ['skill_feedback'],
            source_system: 'aliyun-maxcompute',
          }),
        },
      ]),
    );
    expect(assistantDraftConfirmIds).toEqual(['assistant_draft_weekly_feedback_insight']);
    expect(jobCreateBodies).toEqual([]);
  });

  it('resolves assistant prerequisite drafts when opening a scheduled job draft', async () => {
    const { assistantDraftConfirmIds, assistantDraftPatchBodies, jobCreateBodies } = installScheduledJobsFetchMock();
    window.sessionStorage.setItem(
      assistantScopedStorageKey(ASSISTANT_DRAFT_RESOLUTION_STORAGE_KEY),
      JSON.stringify({
        assistant_draft_code_inspection_ai_agent: {
          resource_id: 'agent_insight',
          resource_type: 'ai_agent',
          title: '代码巡检 AI角色',
        },
        assistant_draft_code_inspection_ai_skill: {
          resource_id: 'skill_feedback',
          resource_type: 'ai_skill',
          title: '代码巡检分析 Skill',
        },
        assistant_draft_github_plugin_action: {
          resource_id: 'plugin_action_github_scan',
          resource_type: 'plugin_action',
          title: 'GitHub 代码巡检执行',
        },
        assistant_draft_github_plugin_connection: {
          resource_id: 'connection_github_prod',
          resource_type: 'plugin_connection',
          title: 'GitHub API 连接',
        },
      }),
    );
    window.sessionStorage.setItem(
      assistantScopedStorageKey(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY),
      JSON.stringify({
        draftId: 'assistant_draft_code_repository_inspection',
        payload: {
          assistant_prerequisite_draft_ids: [
            'assistant_draft_code_inspection_ai_skill',
            'assistant_draft_code_inspection_ai_agent',
            'assistant_draft_github_plugin_connection',
            'assistant_draft_github_plugin_action',
          ],
          cron_expression: '0 2 * * MON',
          enabled: true,
          execution_mode: 'ai_generated',
          job_type: 'code_repository_inspection',
          agent_id: null,
          model_gateway_config_id: 'model_gateway_scheduled_job',
          name: '代码仓库质量安全规范巡检',
          plugin_action_id: null,
          plugin_connection_id: null,
          product_id: 'product_ai_brain',
          schedule_type: 'cron',
          skill_ids: [],
          source_system: 'code-inspection',
        },
        title: '代码仓库质量安全规范巡检',
      }),
    );

    render(<ScheduledJobsPage />);

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(assistantDraftPatchBodies[0]).toMatchObject({
        payload: expect.objectContaining({
          agent_id: 'agent_insight',
          job_type: 'code_repository_inspection',
          name: '代码仓库质量安全规范巡检',
          plugin_action_id: 'plugin_action_github_scan',
          plugin_connection_id: 'connection_github_prod',
          skill_ids: ['skill_feedback'],
        }),
      }),
    );
    expect(assistantDraftConfirmIds).toEqual(['assistant_draft_code_repository_inspection']);
    expect(jobCreateBodies).toEqual([]);
  });

  it('requires AI assembly before saving AI scheduled job types', async () => {
    const { jobCreateBodies } = installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('作业类型')).toBeInTheDocument());
    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '每周反馈 AI 洞察' } });
    fireEvent.mouseDown(within(dialog).getByLabelText('作业类型'));
    const feedbackJobTypeOptions = await screen.findAllByText('用户反馈洞察抽取（取数 + AI 分析 + 写入）');
    expect(feedbackJobTypeOptions.length).toBeGreaterThan(0);
    expect(screen.queryByText('线上日志 AI 分析')).not.toBeInTheDocument();
    fireEvent.click(feedbackJobTypeOptions[feedbackJobTypeOptions.length - 1]);

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() => expect(within(dialog).getByText('请选择 AI 模型')).toBeInTheDocument());
    expect(within(dialog).getByText('请选择 AI角色')).toBeInTheDocument();
    expect(within(dialog).getByText('请选择 Skills')).toBeInTheDocument();
    expect(jobCreateBodies).toEqual([]);
  });

  it('requires Skills even when the other AI job references are selected', async () => {
    const { jobCreateBodies } = installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('名称')).toBeInTheDocument());
    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '每周反馈 AI 洞察' } });

    fireEvent.mouseDown(within(dialog).getByLabelText('所属产品'));
    fireEvent.click(await screen.findByText('AI Brain (ai-brain)'));
    fireEvent.mouseDown(within(dialog).getByLabelText('数据连接'));
    fireEvent.click(await screen.findByText('生产 MaxCompute 项目'));
    fireEvent.mouseDown(within(dialog).getByLabelText('AI 模型'));
    fireEvent.click(await screen.findByText('定时作业模型 (scheduled-job-model)'));
    fireEvent.mouseDown(within(dialog).getByLabelText('AI角色'));
    fireEvent.click(await screen.findByText('洞察 Agent (insight_agent)'));
    fireEvent.mouseDown(within(dialog).getByLabelText('写入策略'));
    fireEvent.click(await screen.findByText('写入用户洞察表'));

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() => expect(within(dialog).getByText('请选择 Skills')).toBeInTheDocument());
    expect(within(dialog).queryByText('请选择 AI 模型')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('请选择 AI角色')).not.toBeInTheDocument();
    expect(jobCreateBodies).toEqual([]);
  });

  it('requires AI assembly when code inspection switches to AI execution mode', async () => {
    const { jobCreateBodies } = installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('作业模板')).toBeInTheDocument());
    fireEvent.mouseDown(within(dialog).getByLabelText('作业模板'));
    fireEvent.click(await screen.findByText('代码仓库质量 / 安全 / 规范巡检'));
    expect(within(dialog).getByText('生产 GitHub 组织')).toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('AI执行'));
    fireEvent.click(await screen.findByTitle('AI 生成'));

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() => expect(within(dialog).getByText('请选择 AI 模型')).toBeInTheDocument());
    expect(within(dialog).getByText('请选择 AI角色')).toBeInTheDocument();
    expect(within(dialog).getByText('请选择 Skills')).toBeInTheDocument();
    expect(jobCreateBodies).toEqual([]);
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
          next_run_at: '2026-06-21T02:47:12.123456+00:00',
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
    expect(screen.getByText('生产 MaxCompute 项目')).toBeInTheDocument();
    expect(screen.getByText('AI 生成 · 定时作业模型 · 洞察 Agent · 1 Skill')).toBeInTheDocument();
    expect(screen.getByText('获取本周用户反馈数据')).toBeInTheDocument();
    expect(screen.getByText('Cron 定时')).toBeInTheDocument();
    expect(screen.getByText('2026-06-21 10:47')).toBeInTheDocument();
    expect(screen.queryByText(/2026-06-21T02:47:12/)).not.toBeInTheDocument();
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

  it('shows code inspection provider connections while hiding unrelated plugin connections', async () => {
    installScheduledJobsFetchMock({
      jobs: [
        {
          cron_expression: '0 2 * * MON',
          enabled: true,
          execution_mode: 'deterministic',
          id: 'scheduled_job_weekly_feedback',
          job_type: 'code_repository_inspection',
          name: '醉清风APP代码仓库质量安全规范巡检',
          plugin_action_id: 'plugin_action_github_scan',
          plugin_connection_id: 'connection_github_prod',
          product_id: 'product_ai_brain',
          schedule_type: 'cron',
          source_system: 'code-inspection',
          status: 'active',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    expect(await screen.findByText('醉清风APP代码仓库质量安全规范巡检')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '编辑作业 醉清风APP代码仓库质量安全规范巡检' }));

    const dialog = await screen.findByRole('dialog', { name: '编辑定时作业' });
    expect(within(dialog).getByText('GitHub 代码巡检')).toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('数据连接'));

    await waitFor(() => expect(screen.getAllByText('生产 GitHub 组织').length).toBeGreaterThan(0));
    expect(screen.queryAllByText('生产 GitLab 项目').length).toBeGreaterThan(0);
    expect(screen.queryAllByText('生产 MaxCompute 项目')).toHaveLength(0);
    expect(screen.queryAllByText('备用 MaxCompute 项目')).toHaveLength(0);
  });

  it('switches code inspection action when selecting a GitLab data connection', async () => {
    const { jobUpdateBodies } = installScheduledJobsFetchMock({
      jobs: [
        {
          cron_expression: '0 2 * * MON',
          enabled: true,
          execution_mode: 'deterministic',
          id: 'scheduled_job_weekly_feedback',
          job_type: 'code_repository_inspection',
          name: '醉清风APP代码仓库质量安全规范巡检',
          plugin_action_id: 'plugin_action_github_scan',
          plugin_connection_id: 'connection_github_prod',
          product_id: 'product_ai_brain',
          schedule_type: 'cron',
          source_system: 'code-inspection',
          status: 'active',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    expect(await screen.findByText('醉清风APP代码仓库质量安全规范巡检')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '编辑作业 醉清风APP代码仓库质量安全规范巡检' }));

    const dialog = await screen.findByRole('dialog', { name: '编辑定时作业' });
    fireEvent.mouseDown(within(dialog).getByLabelText('数据连接'));
    fireEvent.click(await screen.findByText('生产 GitLab 项目'));

    await waitFor(() =>
      expect(within(dialog).getByText('GitLab 代码巡检')).toBeInTheDocument(),
    );

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(jobUpdateBodies[0]).toMatchObject({
        plugin_action_id: 'plugin_action_gitlab_scan',
        plugin_action_ids: ['plugin_action_gitlab_scan'],
        plugin_connection_id: 'connection_gitlab_prod',
        plugin_connection_ids: ['connection_gitlab_prod'],
      }),
    );
  });

  it('submits an explicit scan branch for code inspection jobs', async () => {
    const { jobUpdateBodies } = installScheduledJobsFetchMock({
      jobs: [
        {
          config_json: { repository_id: 'repo_zqf' },
          cron_expression: '0 2 * * MON',
          enabled: true,
          execution_mode: 'deterministic',
          id: 'scheduled_job_weekly_feedback',
          job_type: 'code_repository_inspection',
          name: '醉清风APP代码仓库质量安全规范巡检',
          plugin_action_id: 'plugin_action_gitlab_scan',
          plugin_connection_id: 'connection_gitlab_prod',
          product_id: 'product_ai_brain',
          schedule_type: 'cron',
          source_system: 'code-inspection',
          status: 'active',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    expect(await screen.findByText('醉清风APP代码仓库质量安全规范巡检')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '编辑作业 醉清风APP代码仓库质量安全规范巡检' }));

    const dialog = await screen.findByRole('dialog', { name: '编辑定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('代码仓库')).toBeInTheDocument());
    await waitFor(() => expect(within(dialog).getByLabelText('扫描分支')).toHaveValue('main'));

    fireEvent.change(within(dialog).getByLabelText('扫描分支'), {
      target: { value: 'release/2026.06' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(jobUpdateBodies[0]).toMatchObject({
        config_json: {
          branch: 'release/2026.06',
          repository_id: 'repo_zqf',
        },
      }),
    );
  });

  it('submits native full scan mode without requiring a plugin connection', async () => {
    const { jobUpdateBodies } = installScheduledJobsFetchMock({
      jobs: [
        {
          config_json: {
            branch: 'release/native-scan',
            repository_id: 'repo_zqf',
            scan_mode: 'native_full_scan',
          },
          enabled: true,
          execution_mode: 'deterministic',
          id: 'scheduled_job_native_scan',
          job_type: 'code_repository_inspection',
          name: '醉清风APP本地完整代码扫描',
          plugin_action_id: undefined,
          plugin_connection_id: undefined,
          product_id: 'product_ai_brain',
          schedule_type: 'manual',
          source_system: 'native-code-scanner',
          status: 'active',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    expect(await screen.findByText('醉清风APP本地完整代码扫描')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '编辑作业 醉清风APP本地完整代码扫描' }));

    const dialog = await screen.findByRole('dialog', { name: '编辑定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('代码仓库')).toBeInTheDocument());
    fireEvent.mouseDown(within(dialog).getByLabelText('扫描方式'));
    fireEvent.click((await screen.findAllByText('本地完整扫描（clone 仓库）')).at(-1)!);
    expect(within(dialog).getByLabelText('扫描分支')).toHaveValue('release/native-scan');

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(jobUpdateBodies[0]).toMatchObject({
        config_json: {
          branch: 'release/native-scan',
          repository_id: 'repo_zqf',
          scan_mode: 'native_full_scan',
        },
        plugin_action_id: null,
        plugin_action_ids: [],
        plugin_connection_id: null,
        plugin_connection_ids: [],
      }),
    );
  });

  it('copies an existing scheduled job as a new template draft', async () => {
    const { jobCreateBodies } = installScheduledJobsFetchMock({
      jobs: [
        {
          agent_id: 'agent_insight',
          config_json: { owner: 'ops' },
          cron_expression: '0 9 * * MON',
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
          plugin_output_mapping: { write_target: 'user_feedback_insights' },
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
    fireEvent.click(screen.getByRole('button', { name: '复制作业 每周用户反馈洞察' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    expect(within(dialog).getByLabelText('当前复制来源')).toHaveTextContent('作业');
    expect(within(dialog).getByLabelText('当前复制来源')).toHaveTextContent('每周用户反馈洞察');
    expect(within(dialog).getByLabelText('名称')).toHaveValue('每周用户反馈洞察 副本');
    expect(within(dialog).getByText('生产 MaxCompute 项目')).toBeInTheDocument();
    expect(within(dialog).getByText('定时作业模型 (scheduled-job-model)')).toBeInTheDocument();
    expect(within(dialog).getByText('洞察 Agent (insight_agent)')).toBeInTheDocument();
    expect(within(dialog).getByText('每周反馈分析 (weekly_feedback_analysis)')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('0 9 * * MON')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(jobCreateBodies[0]).toMatchObject({
        agent_id: 'agent_insight',
        config_json: {
          owner: 'ops',
          template_source: {
            source_id: 'scheduled_job_weekly_feedback',
            source_type: 'scheduled_job',
            title: '每周用户反馈洞察',
          },
        },
        cron_expression: '0 9 * * MON',
        execution_mode: 'ai_generated',
        job_type: 'user_feedback_insight_extract',
        knowledge_document_ids: ['knowledge_payment_runbook'],
        model_gateway_config_id: 'model_gateway_scheduled_job',
        name: '每周用户反馈洞察 副本',
        plugin_action_id: 'plugin_action_maxcompute',
        plugin_connection_id: 'connection_maxcompute_prod',
        plugin_input_mapping: {
          week_end: '{{last_full_week.end}}',
          week_start: '{{last_full_week.start}}',
        },
        plugin_output_mapping: { write_target: 'user_feedback_insights' },
        product_id: 'product_ai_brain',
        schedule_type: 'cron',
        skill_ids: ['skill_feedback'],
        source_system: 'aliyun-maxcompute',
      }),
    );
    expect(jobCreateBodies[0]).not.toHaveProperty('connection_environment');
  });

  it('copies a run snapshot as a new scheduled job template draft', async () => {
    const { jobCreateBodies } = installScheduledJobsFetchMock({
      jobs: [
        {
          agent_id: 'agent_insight',
          config_json: { owner: 'ops' },
          cron_expression: '0 9 * * MON',
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
          plugin_output_mapping: { write_target: 'user_feedback_insights' },
          product_id: 'product_ai_brain',
          schedule_type: 'cron',
          skill_ids: ['skill_feedback'],
          source_system: 'aliyun-maxcompute',
          status: 'active',
        },
      ],
      runs: [
        {
          config_snapshot: {
            agent_id: 'agent_insight',
            config_json: { prompt_variant: 'strict' },
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            model_gateway_config_id: 'model_gateway_scheduled_job',
            plugin_action_id: 'plugin_action_maxcompute',
            plugin_connection_id: 'connection_maxcompute_prod',
            product_id: 'product_ai_brain',
            schedule_type: 'cron',
            skill_ids: ['skill_feedback'],
            source_system: 'aliyun-maxcompute',
          },
          id: 'scheduled_job_run_weekly_feedback',
          records_imported: 1,
          result_summary: {},
          scheduled_job_id: 'scheduled_job_weekly_feedback',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    fireEvent.click(await screen.findByRole('button', { name: '复制运行配置 scheduled_job_run_weekly_feedback' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    expect(within(dialog).getByLabelText('当前复制来源')).toHaveTextContent('运行记录');
    expect(within(dialog).getByLabelText('当前复制来源')).toHaveTextContent('scheduled_job_run_weekly_feedback');
    expect(within(dialog).getByLabelText('名称')).toHaveValue('每周用户反馈洞察 运行快照副本');
    expect(within(dialog).getByText('生产 MaxCompute 项目')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(jobCreateBodies[0]).toMatchObject({
        config_json: {
          prompt_variant: 'strict',
          template_source: {
            source_id: 'scheduled_job_run_weekly_feedback',
            source_type: 'scheduled_job_run',
            title: 'scheduled_job_weekly_feedback',
          },
        },
        name: '每周用户反馈洞察 运行快照副本',
        plugin_input_mapping: {
          week_end: '{{last_full_week.end}}',
          week_start: '{{last_full_week.start}}',
        },
        plugin_output_mapping: { write_target: 'user_feedback_insights' },
      }),
    );
  });

  it('shows template source labels in run details without adding a job list column', async () => {
    installScheduledJobsFetchMock({
      jobs: [
        {
          config_json: {
            template_source: {
              source_id: 'scheduled_job_original_weekly_feedback',
              source_type: 'scheduled_job',
              title: '原始周反馈作业',
            },
          },
          execution_mode: 'ai_generated',
          id: 'scheduled_job_copied_weekly_feedback',
          job_type: 'user_feedback_insight_extract',
          name: '复制后的周反馈作业',
          plugin_action_id: 'plugin_action_maxcompute',
          plugin_connection_id: 'connection_maxcompute_prod',
          schedule_type: 'manual',
          status: 'active',
        },
      ],
      runs: [
        {
          config_snapshot: {
            config_json: {
              template_source: {
                source_id: 'scheduled_job_run_original_weekly_feedback',
                source_type: 'scheduled_job_run',
                title: '原始运行快照',
              },
            },
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
          },
          id: 'scheduled_job_run_copied_weekly_feedback',
          records_imported: 1,
          result_summary: {},
          scheduled_job_id: 'scheduled_job_copied_weekly_feedback',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    expect(await screen.findByText('复制后的周反馈作业')).toBeInTheDocument();
    expect(screen.queryByText('模板来源')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('模板来源 scheduled_job_original_weekly_feedback')).not.toBeInTheDocument();

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看运行结果 scheduled_job_run_copied_weekly_feedback' }));

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    expect(within(dialog).getByLabelText('模板来源 scheduled_job_run_original_weekly_feedback')).toHaveTextContent(
      '运行快照',
    );
    expect(within(dialog).getByLabelText('模板来源 scheduled_job_run_original_weekly_feedback')).toHaveTextContent(
      '原始运行快照',
    );
  });

  it('shows scheduled job run result details', async () => {
    const exportedBlobs: Blob[] = [];
    const createObjectURL = vi.fn((blob: Blob) => {
      exportedBlobs.push(blob);
      return 'blob:scheduled-job-run-detail';
    });
    const revokeObjectURL = vi.fn();
    const clickDownload = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => undefined);
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL,
      revokeObjectURL,
    });
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
                connection_environment: 'prod',
                input_mapping: {
                  week_end: '20260608',
                  week_start: '20260601',
                },
                latency_ms: 318,
                records_imported: 18,
                request_method: 'GET',
                request_url: 'https://maxcompute.example.com/feedback?start_pt=20260601&end_pt=20260608',
                response_status_code: 200,
                response_summary: {
                  json: {
                    row_count: 18,
                  },
                  status_code: 200,
                },
                status: 'succeeded',
              },
              result_action: {
                created_ids: ['insight_001'],
                records_imported: 1,
                status: 'succeeded',
                write_target: 'user_feedback_insights',
              },
              result_actions: [
                {
                  status: 'succeeded',
                  type: 'write_result',
                  write_target: 'user_feedback_insights',
                },
              ],
              skill_processing: {
                model_gateway_called: true,
                model_log_id: 'model_log_weekly_feedback',
                note: '数据连接返回内容已通过平台 AI 大模型处理为结果写入可消费的结构化 JSON。',
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
            trace_graph: {
              edges: [
                { from: 'data_connection', to: 'skill_processing' },
                { from: 'skill_processing', to: 'result_action' },
              ],
              nodes: [
                {
                  duration_ms: 318,
                  error: null,
                  id: 'data_connection',
                  input: { week_start: '20260601' },
                  label: '数据连接获取内容',
                  output: { records_imported: 18, response_status_code: 200 },
                  retry_count: 1,
                  status: 'succeeded',
                },
                {
                  duration_ms: 860,
                  error: null,
                  id: 'skill_processing',
                  input: { source_row_count: 18 },
                  label: '经过 Skill 处理后的内容',
                  output: { candidate_count: 1 },
                  retry_count: 1,
                  status: 'succeeded',
                },
                {
                  duration_ms: 42,
                  error: null,
                  id: 'result_action',
                  input: { write_target: 'user_feedback_insights' },
                  label: '结果写入反馈内容',
                  output: { created_ids: ['insight_001'] },
                  retry_count: 1,
                  status: 'succeeded',
                },
              ],
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
    expect(within(dialog).getByRole('link', { name: '执行诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=scheduled_job_run_weekly_feedback&source_type=scheduled_job_run',
    );
    expect(within(dialog).getByText('运行链路')).toBeInTheDocument();
    expect(within(dialog).getAllByText('2026-06-11 18:00').length).toBeGreaterThanOrEqual(2);
    expect(within(dialog).getByLabelText('流程节点 数据连接获取内容')).toHaveTextContent('succeeded');
    expect(within(dialog).getByLabelText('流程节点 数据连接获取内容')).toHaveTextContent('prod');
    expect(within(dialog).getByLabelText('流程节点 数据连接获取内容')).toHaveTextContent('GET');
    expect(within(dialog).getByLabelText('流程节点 数据连接获取内容')).toHaveTextContent('200');
    expect(within(dialog).getByLabelText('流程节点 数据连接获取内容')).toHaveTextContent('318');
    expect(within(dialog).getByLabelText('流程节点 数据连接获取内容')).toHaveTextContent('maxcompute.example.com');
    expect(within(dialog).getByLabelText('流程节点 AI执行处理内容')).toHaveTextContent('已调用');
    expect(within(dialog).getByLabelText('流程节点 AI执行处理内容')).toHaveTextContent('1');
    expect(within(dialog).getByLabelText('流程节点 动作反馈内容')).toHaveTextContent('user_feedback_insights');
    expect(within(dialog).getByLabelText('流程节点 动作反馈内容')).toHaveTextContent('insight_001');
    expect(within(dialog).getAllByText('数据连接获取内容').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('AI执行处理内容').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('动作反馈内容').length).toBeGreaterThan(0);
    expect(within(dialog).getByText('运行 Trace DAG')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('318ms');
    expect(within(dialog).getByLabelText('Trace 节点 经过 Skill 处理后的内容')).toHaveTextContent('860ms');
    expect(within(dialog).getByText('data_connection → skill_processing')).toBeInTheDocument();
    expect(within(dialog).getByText('skill_processing → result_action')).toBeInTheDocument();
    expect(within(dialog).getByText('动作执行状态')).toBeInTheDocument();
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
    expect(dialog).toHaveTextContent('write_result');
    const askAiLink = within(dialog).getByRole('link', { name: '问 AI' });
    expect(askAiLink).toHaveAttribute('href');
    const href = askAiLink.getAttribute('href') ?? '';
    expect(href.startsWith('/assistant?')).toBe(true);
    const assistantParams = new URLSearchParams(href.split('?')[1]);
    expect(assistantParams.get('reference_type')).toBe('scheduled_job_run');
    expect(assistantParams.get('reference_id')).toBe('scheduled_job_run_weekly_feedback');
    expect(assistantParams.get('prompt')).toBe('帮我分析这次运行结果');

    fireEvent.click(within(dialog).getByRole('button', { name: '转业务草案' }));
    const insightDraftLink = await screen.findByRole('link', { name: '转洞察草案' });
    expect(insightDraftLink).toHaveAttribute('href');
    const insightDraftHref = insightDraftLink.getAttribute('href') ?? '';
    expect(insightDraftHref.startsWith('/assistant?')).toBe(true);
    const insightDraftParams = new URLSearchParams(insightDraftHref.split('?')[1]);
    expect(insightDraftParams.get('reference_type')).toBe('scheduled_job_run');
    expect(insightDraftParams.get('reference_id')).toBe('scheduled_job_run_weekly_feedback');
    expect(insightDraftParams.get('prompt')).toBe(
      '请基于这次定时作业运行结果生成用户洞察草案，保留数据来源、AI处理结论和结果动作反馈。',
    );
    const requirementDraftLink = screen.getByRole('link', { name: '转需求草案' });
    const requirementDraftHref = requirementDraftLink.getAttribute('href') ?? '';
    const requirementDraftParams = new URLSearchParams(requirementDraftHref.split('?')[1]);
    expect(requirementDraftParams.get('reference_type')).toBe('scheduled_job_run');
    expect(requirementDraftParams.get('reference_id')).toBe('scheduled_job_run_weekly_feedback');
    expect(requirementDraftParams.get('prompt')).toBe(
      '请基于这次定时作业运行结果提炼可落地的需求草案，包含背景、目标、价值、验收标准和建议优先级。',
    );
    const bugDraftLink = screen.getByRole('link', { name: '转 Bug 草案' });
    const bugDraftHref = bugDraftLink.getAttribute('href') ?? '';
    const bugDraftParams = new URLSearchParams(bugDraftHref.split('?')[1]);
    expect(bugDraftParams.get('reference_type')).toBe('scheduled_job_run');
    expect(bugDraftParams.get('reference_id')).toBe('scheduled_job_run_weekly_feedback');
    expect(bugDraftParams.get('prompt')).toBe(
      '请基于这次定时作业运行结果识别需要跟进的缺陷或异常，生成 Bug 草案，包含复现线索、影响范围、严重级别和建议处理人。',
    );

    fireEvent.click(within(dialog).getByRole('button', { name: '导出 JSON' }));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(clickDownload).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:scheduled-job-run-detail');
    expect(exportedBlobs[0]).toBeInstanceOf(Blob);
    const exportPayload = buildScheduledJobRunDetailExportPayload({
      agentLabel: '洞察 Agent',
      executionModeLabel: 'AI 生成',
      jobTypeLabel: '用户反馈洞察抽取（取数 + AI 分析 + 写入）',
      modelLabel: '定时作业模型',
      resultWriteRecords: [],
      run: {
        id: 'scheduled_job_run_weekly_feedback',
        result_summary: {
          execution_nodes: {
            data_connection: {
              records_imported: 18,
              response_status_code: 200,
              status: 'succeeded',
            },
            result_action: {
              created_ids: ['insight_001'],
              status: 'succeeded',
            },
            skill_processing: {
              output: { candidate_count: 1 },
              status: 'succeeded',
            },
          },
        },
        status: 'succeeded',
      } as ScheduledJobRunRecord,
      skillLabels: '每周反馈分析',
    });
    expect(exportPayload).toMatchObject({
      export_version: 'scheduled_job_run_detail.v1',
      labels: {
        agent: '洞察 Agent',
        execution_mode: 'AI 生成',
        job_type: '用户反馈洞察抽取（取数 + AI 分析 + 写入）',
        model: '定时作业模型',
        skills: '每周反馈分析',
      },
      run: {
        id: 'scheduled_job_run_weekly_feedback',
      },
      sections: {
        ai_processing: {
          output: { candidate_count: 1 },
          status: 'succeeded',
        },
        data_connection: {
          records_imported: 18,
          response_status_code: 200,
          status: 'succeeded',
        },
        result_action: {
          created_ids: ['insight_001'],
          status: 'succeeded',
        },
      },
    });
  });

  it('generates a scheduled job template from a successful run', async () => {
    const { generatedTemplateRequests, jobCreateBodies } = installScheduledJobsFetchMock({
      runs: [
        {
          config_snapshot: {
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            name: '每周反馈运行',
          },
          finished_at: '2026-06-11T10:00:03Z',
          id: 'scheduled_job_run_weekly_feedback',
          records_imported: 1,
          result_summary: {
            execution_nodes: {
              data_connection: { records_imported: 18, status: 'succeeded' },
              result_action: { records_imported: 1, status: 'succeeded' },
              skill_processing: { model_gateway_called: true, status: 'succeeded' },
            },
          },
          scheduled_job_id: 'scheduled_job_weekly_feedback',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看运行结果 scheduled_job_run_weekly_feedback' }));

    const detailDialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    fireEvent.click(within(detailDialog).getByRole('button', { name: '生成模板' }));

    await waitFor(() => expect(generatedTemplateRequests).toEqual(['scheduled_job_run_weekly_feedback']));
    const createDialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    expect(within(createDialog).getByLabelText('名称')).toHaveValue('每周反馈运行模板');
    expect(within(createDialog).getByText('执行链路')).toBeInTheDocument();
    expect(within(createDialog).getByText('运行记录')).toBeInTheDocument();

    fireEvent.click(within(createDialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(jobCreateBodies[0]).toMatchObject({
        config_json: {
          template_source: {
            source_id: 'scheduled_job_run_weekly_feedback',
            source_type: 'scheduled_job_run',
          },
        },
        name: '每周反馈运行模板',
        plugin_action_id: 'plugin_action_maxcompute',
        plugin_connection_id: 'connection_maxcompute_prod',
      }),
    );
  });

  it('shows AI executor runner details in scheduled job run results', async () => {
    installScheduledJobsFetchMock({
      runs: [
        {
          collector_run_id: 'collector_run_openclaw_scan',
          config_snapshot: {
            execution_mode: 'deterministic',
            job_type: 'plugin_action_invoke',
          },
          finished_at: '2026-06-11T10:00:10Z',
          id: 'scheduled_job_run_openclaw_scan',
          plugin_invocation_log_id: 'plugin_invocation_log_openclaw_scan',
          records_imported: 2,
          result_summary: {
            execution_nodes: {
              data_connection: {
                connection_environment: 'dev',
                records_imported: 0,
                status: 'succeeded',
              },
              result_action: {
                feedback: {
                  runner_result: {
                    finding_count: 2,
                    summary: '发现 2 个中风险规范问题',
                  },
                },
                records_imported: 2,
                status: 'succeeded',
                write_target: 'scheduled_job_result',
              },
              runner_execution: {
                executor_type: 'openclaw',
                finished_at: '2026-06-11T10:00:09Z',
                logs: [{ level: 'info', message: 'openclaw scan finished' }],
                result_json: {
                  finding_count: 2,
                  summary: '发现 2 个中风险规范问题',
                },
                runner_id: 'ai_executor_runner_local',
                runner_task_id: 'ai_executor_task_openclaw_scan',
                status: 'succeeded',
                workspace_root: '/Users/zeek/source/e-ai-brain',
              },
              skill_processing: {
                model_gateway_called: false,
                processing_mode: 'plugin_structured_output',
                status: 'not_run',
              },
            },
          },
          scheduled_job_id: 'scheduled_job_openclaw_scan',
          started_at: '2026-06-11T10:00:00Z',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看运行结果 scheduled_job_run_openclaw_scan' }));

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    expect(within(dialog).getByLabelText('流程节点 AI 执行器执行内容')).toHaveTextContent('openclaw');
    expect(within(dialog).getByLabelText('流程节点 AI 执行器执行内容')).toHaveTextContent('ai_executor_runner_local');
    expect(within(dialog).getByLabelText('流程节点 AI 执行器执行内容')).toHaveTextContent('ai_executor_task_openclaw_scan');
    expect(within(dialog).getByLabelText('流程节点 AI 执行器执行内容')).toHaveTextContent('/Users/zeek/source/e-ai-brain');
    expect(within(dialog).getByLabelText('流程节点 AI 执行器执行内容')).toHaveTextContent('1');
    expect(within(dialog).getByLabelText('流程节点 动作反馈内容')).toHaveTextContent('scheduled_job_result');
    expect(dialog).toHaveTextContent('发现 2 个中风险规范问题');
  });

  it('shows system default AI executor model details in scheduled job run results', async () => {
    installScheduledJobsFetchMock({
      runs: [
        {
          collector_run_id: 'collector_run_system_executor_scan',
          config_snapshot: {
            execution_mode: 'deterministic',
            job_type: 'plugin_action_invoke',
          },
          finished_at: '2026-06-14T10:00:05Z',
          id: 'scheduled_job_run_system_executor_scan',
          records_imported: 1,
          result_summary: {
            execution_nodes: {
              data_connection: {
                records_imported: 0,
                status: 'succeeded',
              },
              result_action: {
                feedback: {
                  runner_result: {
                    summary: '系统默认模型完成仓库分析',
                  },
                },
                records_imported: 1,
                status: 'succeeded',
                write_target: 'scheduled_job_result',
              },
              runner_execution: {
                executor_type: 'model_gateway',
                model_gateway_log_id: 'model_gateway_log_system_executor',
                result_json: {
                  summary: '系统默认模型完成仓库分析',
                },
                runner_id: 'ai_executor_runner_system_default',
                status: 'succeeded',
                workspace_root: '/Users/zeek/source/e-ai-brain',
              },
              skill_processing: {
                model_gateway_called: false,
                processing_mode: 'plugin_structured_output',
                status: 'not_run',
              },
            },
          },
          scheduled_job_id: 'scheduled_job_system_executor_scan',
          started_at: '2026-06-14T10:00:00Z',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    fireEvent.click(
      await screen.findByRole('button', { name: '查看运行结果 scheduled_job_run_system_executor_scan' }),
    );

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    const executorNode = within(dialog).getByLabelText('流程节点 AI 执行器执行内容');
    expect(executorNode).toHaveTextContent('执行器实例');
    expect(executorNode).toHaveTextContent('model_gateway');
    expect(executorNode).toHaveTextContent('ai_executor_runner_system_default');
    expect(executorNode).toHaveTextContent('model_gateway_log_system_executor');
    expect(executorNode).toHaveTextContent('系统默认模型完成仓库分析');
  });

  it('shows email notification feedback in the result action node', async () => {
    const { resultWriteRecordCalls } = installScheduledJobsFetchMock({
      resultWriteRecords: [
        {
          created_at: '2026-06-13T10:00:00Z',
          feedback: {
            delivery_id: 'mail_001',
            delivery_status: 'queued',
            sample_records: ['owner@example.com'],
            subject: '定时作业完成',
          },
          id: 'result_write_record_scheduled_job_run_email_notification',
          plugin_action_id: 'plugin_action_email_notification',
          plugin_invocation_log_id: 'plugin_invocation_log_email_notification',
          records_imported: 1,
          scheduled_job_id: 'scheduled_job_email_notification',
          scheduled_job_run_id: 'scheduled_job_run_email_notification',
          source_type: 'scheduled_job_run',
          status: 'succeeded',
          summary_fields: {
            delivery_id: 'mail_001',
            delivery_status: 'queued',
            sample_records: ['owner@example.com'],
            subject: '定时作业完成',
          },
          write_target: 'email_notifications',
          write_target_label: '邮件通知记录',
        },
      ],
      runs: [
        {
          id: 'scheduled_job_run_email_notification',
          records_imported: 1,
          result_summary: {
            execution_nodes: {
              result_action: {
                action_id: 'plugin_action_email_notification',
                feedback: {
                  delivery_id: 'mail_001',
                  delivery_status: 'queued',
                  sample_records: ['owner@example.com'],
                  subject: '定时作业完成',
                },
                records_imported: 1,
                status: 'succeeded',
                write_target: 'email_notifications',
                write_target_label: '邮件通知记录',
              },
            },
          },
          scheduled_job_id: 'scheduled_job_email_notification',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看运行结果 scheduled_job_run_email_notification' }));

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    const resultActionNode = within(dialog).getByLabelText('流程节点 动作反馈内容');
    expect(resultActionNode).toHaveTextContent('邮件通知记录');
    expect(resultActionNode).toHaveTextContent('mail_001');
    expect(resultActionNode).toHaveTextContent('queued');
    expect(resultActionNode).toHaveTextContent('owner@example.com');
    expect(within(dialog).getByText('结果写入记录')).toBeInTheDocument();
    expect(await within(dialog).findByText('plugin_invocation_log_email_notification')).toBeInTheDocument();
    expect(within(dialog).getByText('2026-06-13 18:00')).toBeInTheDocument();
    expect(within(dialog).getAllByText('邮件通知记录').length).toBeGreaterThan(0);
    await waitFor(() =>
      expect(resultWriteRecordCalls).toContain(
        '/api/system/result-write-records?scheduled_job_run_id=scheduled_job_run_email_notification',
      ),
    );
  });

  it('shows AI code inspection run results in the same three-stage detail chain', async () => {
    installScheduledJobsFetchMock({
      runs: [
        {
          collector_run_id: 'collector_run_code_inspection_ai',
          config_snapshot: {
            agent_id: 'agent_insight',
            execution_mode: 'ai_generated',
            job_type: 'code_repository_inspection',
            model_gateway_config_id: 'model_gateway_scheduled_job',
            skill_ids: ['skill_feedback'],
          },
          finished_at: '2026-06-11T02:01:00Z',
          id: 'scheduled_job_run_code_inspection_ai',
          plugin_invocation_log_id: 'plugin_invocation_log_code_scan',
          records_imported: 1,
          resolved_agent_snapshot: {
            code: 'code_inspection_agent',
            id: 'agent_insight',
            name: '洞察 Agent',
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
              code_inspection_report: {
                finding_count: 1,
                report_id: 'code_inspection_report_ai',
                risk_level: 'critical',
                severe_finding_count: 1,
                status: 'succeeded',
              },
              data_connection: {
                records_imported: 2,
                response_summary: {
                  json: {
                    findings: [{ rule_id: 'SEC001' }, { rule_id: 'QLT010' }],
                  },
                },
                status: 'succeeded',
              },
              result_action: {
                feedback: {
                  report_id: 'code_inspection_report_ai',
                },
                records_imported: 1,
                status: 'succeeded',
                write_target: 'code_inspection_reports',
              },
              result_actions: [
                {
                  action_type: 'write_code_inspection_report',
                  report_id: 'code_inspection_report_ai',
                  status: 'succeeded',
                },
              ],
              skill_processing: {
                model_gateway_called: true,
                model_log_id: 'model_log_code_inspection',
                output: {
                  finding_count: 1,
                  risk_level: 'critical',
                  summary: 'AI 复核确认 1 个 critical 安全问题。',
                },
                processing_mode: 'model_gateway_json_transform',
                skill_codes: ['code_inspection_analysis'],
                status: 'succeeded',
              },
              task_creation: {
                created_task_ids: ['task_code_fix_001'],
                feedback: {
                  task_ids: ['task_code_fix_001'],
                },
                records_imported: 1,
                status: 'succeeded',
              },
            },
            finding_count: 1,
            report_id: 'code_inspection_report_ai',
            risk_level: 'critical',
            task_ids: ['task_code_fix_001'],
            write_target: 'code_inspection_reports',
          },
          scheduled_job_id: 'scheduled_job_code_inspection_ai',
          started_at: '2026-06-11T02:00:00Z',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看运行结果 scheduled_job_run_code_inspection_ai' }));

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    expect(within(dialog).getByRole('link', { name: '执行诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=scheduled_job_run_code_inspection_ai&source_type=scheduled_job_run',
    );
    expect(within(dialog).getByText('运行链路')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('流程节点 数据连接获取内容')).toHaveTextContent('succeeded');
    expect(within(dialog).getByLabelText('流程节点 AI执行处理内容')).toHaveTextContent('已调用');
    expect(within(dialog).getByLabelText('流程节点 动作反馈内容')).toHaveTextContent('code_inspection_reports');
    expect(dialog).toHaveTextContent('代码仓库巡检');
    expect(dialog).toHaveTextContent('代码巡检报告写入结果');
    expect(dialog).toHaveTextContent('严重问题自动创建整改任务');
    expect(dialog).toHaveTextContent('task_code_fix_001');
    expect(dialog).toHaveTextContent('code_inspection_report_ai');
    expect(dialog).toHaveTextContent('model_log_code_inspection');
    expect(dialog).toHaveTextContent('write_code_inspection_report');
  });

  it('opens a scheduled job run detail from route query parameters', async () => {
    window.history.pushState({}, '', '/tasks/scheduled-jobs?tab=runs&run_id=scheduled_job_run_deep_link');
    installScheduledJobsFetchMock({
      runs: [
        {
          config_snapshot: {
            execution_mode: 'ai_generated',
            job_type: 'code_repository_inspection',
          },
          id: 'scheduled_job_run_deep_link',
          plugin_invocation_log_id: 'plugin_invocation_log_deep_link',
          records_imported: 3,
          result_summary: {
            execution_nodes: {
              result_action: {
                status: 'succeeded',
                write_target: 'code_inspection_reports',
              },
            },
          },
          scheduled_job_id: 'scheduled_job_code_inspection_weekly',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    expect(dialog).toHaveTextContent('scheduled_job_run_deep_link');
    expect(dialog).toHaveTextContent('代码仓库巡检');
    expect(dialog).toHaveTextContent('plugin_invocation_log_deep_link');
    expect(screen.getByRole('tab', { name: '运行记录' })).toHaveAttribute('aria-selected', 'true');
  });

  it('opens and expands the linked result write record from route query parameters', async () => {
    window.history.pushState(
      {},
      '',
      '/tasks/scheduled-jobs?tab=runs&run_id=scheduled_job_run_write_trace&result_write_record_id=result_write_record_failed_trace',
    );
    const { resultWriteRecordCalls } = installScheduledJobsFetchMock({
      resultWriteRecords: [
        {
          created_at: '2026-06-17T09:00:00Z',
          feedback: {
            error: 'downstream write failed',
          },
          id: 'result_write_record_failed_trace',
          plugin_action_id: 'plugin_action_feedback_write',
          plugin_invocation_log_id: 'plugin_invocation_log_failed_trace',
          records_imported: 0,
          scheduled_job_id: 'scheduled_job_feedback_trace',
          scheduled_job_run_id: 'scheduled_job_run_write_trace',
          source_type: 'scheduled_job_run',
          status: 'failed',
          summary_fields: {
            error: 'downstream write failed',
          },
          write_target: 'user_feedback_insights',
          write_target_label: '用户洞察表',
        },
      ],
      runs: [
        {
          id: 'scheduled_job_run_write_trace',
          records_imported: 0,
          result_summary: {
            execution_nodes: {
              result_action: {
                status: 'failed',
                write_target: 'user_feedback_insights',
                write_target_label: '用户洞察表',
              },
            },
          },
          scheduled_job_id: 'scheduled_job_feedback_trace',
          status: 'failed',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    await waitFor(() =>
      expect(resultWriteRecordCalls).toContain(
        '/api/system/result-write-records?scheduled_job_run_id=scheduled_job_run_write_trace',
      ),
    );
    expect(within(dialog).getByText('结果写入记录')).toBeInTheDocument();
    expect(await within(dialog).findByText('执行反馈')).toBeInTheDocument();
    expect(within(dialog).getAllByText(/downstream write failed/).length).toBeGreaterThan(0);
    expect(screen.getByRole('tab', { name: '运行记录' })).toHaveAttribute('aria-selected', 'true');
  });

  it('can rerun a scheduled job from an existing run record', async () => {
    const { runJobBodies, runJobIds } = installScheduledJobsFetchMock({
      runResponse: Promise.resolve({
        id: 'scheduled_job_run_weekly_feedback_rerun',
        records_imported: 2,
        result_summary: {
          execution_nodes: {
            result_action: {
              records_imported: 2,
              status: 'succeeded',
              write_target: 'user_feedback_insights',
            },
            skill_processing: {
              model_gateway_called: true,
              model_log_id: 'model_log_rerun',
              status: 'succeeded',
            },
          },
        },
        scheduled_job_id: 'scheduled_job_weekly_feedback',
        source_run_id: 'scheduled_job_run_weekly_feedback',
        source_run_summary: {
          error_code: 'MODEL_GATEWAY_FAILED',
          id: 'scheduled_job_run_weekly_feedback',
          records_imported: 1,
          status: 'failed',
          trigger_type: 'manual',
        },
        status: 'succeeded',
        trigger_type: 'manual_rerun',
      }),
      runs: [
        {
          id: 'scheduled_job_run_weekly_feedback',
          records_imported: 1,
          result_summary: {},
          scheduled_job_id: 'scheduled_job_weekly_feedback',
          status: 'failed',
          trigger_type: 'manual',
        },
      ],
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    expect(await screen.findByText('手动触发')).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: '复跑运行 scheduled_job_run_weekly_feedback' }));

    await waitFor(() => expect(runJobIds).toEqual(['scheduled_job_weekly_feedback']));
    expect(runJobBodies).toEqual([
      { source_run_id: 'scheduled_job_run_weekly_feedback', trigger_type: 'manual_rerun' },
    ]);
    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    expect(dialog).toHaveTextContent('scheduled_job_run_weekly_feedback_rerun');
    expect(dialog).toHaveTextContent('运行记录复跑');
    expect(dialog).toHaveTextContent('scheduled_job_run_weekly_feedback');
    expect(dialog).toHaveTextContent('复跑对比');
    expect(dialog).toHaveTextContent('来源运行');
    expect(dialog).toHaveTextContent('MODEL_GATEWAY_FAILED');
    expect(dialog).toHaveTextContent('model_log_rerun');
  });

  it('shows an in-progress state while a scheduled job is running', async () => {
    let resolveRun!: (value: unknown) => void;
    const runResponse = new Promise<unknown>((resolve) => {
      resolveRun = resolve;
    });
    const { runJobBodies } = installScheduledJobsFetchMock({
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
    expect(runJobBodies).toEqual([{ trigger_type: 'manual' }]);

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

  it('shows a failure message when a scheduled job run returns failed', async () => {
    const successSpy = vi.spyOn(message, 'success');
    const errorSpy = vi.spyOn(message, 'error');
    const runResponse = Promise.resolve({
      error_code: 'HTTPError',
      error_message: 'HTTP Error 403: Forbidden',
      id: 'scheduled_job_run_code_inspection_failed',
      records_imported: 0,
      result_summary: {},
      scheduled_job_id: 'scheduled_job_weekly_feedback',
      status: 'failed',
      trigger_type: 'manual',
    });
    installScheduledJobsFetchMock({
      jobs: [
        {
          enabled: true,
          execution_mode: 'ai_generated',
          id: 'scheduled_job_weekly_feedback',
          job_type: 'code_repository_inspection',
          name: '代码仓库质量安全规范巡检',
          plugin_action_id: 'plugin_action_github_scan',
          plugin_connection_id: 'connection_github_prod',
          schedule_type: 'manual',
          skill_ids: ['skill_feedback'],
          status: 'active',
        },
      ],
      runResponse,
    });

    render(<ScheduledJobsPage />);

    expect(await screen.findByText('代码仓库质量安全规范巡检')).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: '运行作业 代码仓库质量安全规范巡检' }));

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    expect(dialog).toHaveTextContent('failed');
    const askAiLink = within(dialog).getByRole('link', { name: '问 AI' });
    const askAiHref = askAiLink.getAttribute('href') ?? '';
    const askAiParams = new URLSearchParams(askAiHref.split('?')[1]);
    expect(askAiParams.get('reference_type')).toBe('scheduled_job_run');
    expect(askAiParams.get('reference_id')).toBe('scheduled_job_run_code_inspection_failed');
    expect(askAiParams.get('prompt')).toBe('为什么这次任务失败？');

    const diagnosticLink = within(dialog).getByRole('link', { name: '继续诊断' });
    const diagnosticHref = diagnosticLink.getAttribute('href') ?? '';
    const diagnosticParams = new URLSearchParams(diagnosticHref.split('?')[1]);
    expect(diagnosticParams.get('reference_type')).toBe('scheduled_job_run');
    expect(diagnosticParams.get('reference_id')).toBe('scheduled_job_run_code_inspection_failed');
    expect(diagnosticParams.get('prompt')).toBe('为什么这次任务失败？');

    const repairDraftLink = within(dialog).getByRole('link', { name: '生成修复草案' });
    const repairDraftHref = repairDraftLink.getAttribute('href') ?? '';
    const repairDraftParams = new URLSearchParams(repairDraftHref.split('?')[1]);
    expect(repairDraftParams.get('reference_type')).toBe('scheduled_job_run');
    expect(repairDraftParams.get('reference_id')).toBe('scheduled_job_run_code_inspection_failed');
    expect(repairDraftParams.get('prompt')).toBe('这次失败怎么修？帮我生成修复草案');

    const compareLink = within(dialog).getByRole('link', { name: '对比上次成功' });
    const compareHref = compareLink.getAttribute('href') ?? '';
    const compareParams = new URLSearchParams(compareHref.split('?')[1]);
    expect(compareParams.get('reference_type')).toBe('scheduled_job_run');
    expect(compareParams.get('reference_id')).toBe('scheduled_job_run_code_inspection_failed');
    expect(compareParams.get('prompt')).toBe('和上次成功有什么不同？');
    await waitFor(() =>
      expect(errorSpy).toHaveBeenCalledWith('作业运行失败：HTTP Error 403: Forbidden'),
    );
    expect(successSpy).not.toHaveBeenCalledWith('作业运行完成');
  });
});
