import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import ScheduledJobsPage from '../src/pages/ScheduledJobs';
import { buildScheduledJobRunDetailExportPayload } from '../src/pages/ScheduledJobs/components/scheduledJobRunDetailExport';
import {
  ASSISTANT_DRAFT_RESOLUTION_STORAGE_KEY,
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  assistantScopedStorageKey,
  type ScheduledJobRunRecord,
} from '../src/services/aiBrain';

function installScheduledJobsFetchMock(
  options: {
    dryRunResponse?: unknown | ((body: Record<string, unknown>) => Promise<unknown> | unknown);
    jobs?: Array<Record<string, unknown>>;
    observability?: unknown;
    resultWriteRecords?: unknown[];
    deferRunListReload?: boolean;
    runResponse?: Promise<unknown>;
    runs?: unknown[];
    traceNodeRerunMode?: 'protected_skill' | 'ready_all';
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
  let runListCallCount = 0;
  const resultWriteRecordCalls: string[] = [];
  const jobs: Array<Record<string, unknown>> = options.jobs ?? [];
  const resultWriteRecords = options.resultWriteRecords ?? [];
  const runs = options.runs ?? [];
  const traceNodeRerunCalls: string[] = [];
  const traceNodeRerunMode = options.traceNodeRerunMode ?? 'protected_skill';
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
  const readyTraceNodeRerunPreview = ({
    controls,
    nodeId,
    safeNextAction = 'confirm_single_node_rerun',
    sideEffectPolicy,
    snapshotPreview,
    stage,
    stageLabel,
  }: {
    controls: Array<Record<string, unknown>>;
    nodeId: string;
    safeNextAction?: string;
    sideEffectPolicy: string;
    snapshotPreview: Record<string, unknown>;
    stage: string;
    stageLabel: string;
  }) => ({
    blocked_by: [],
    can_preview_from_snapshot: true,
    control_summary: {
      blocked_count: 0,
      missing_count: 0,
      needs_review_count: 0,
      satisfied_count: controls.length,
      total: controls.length,
    },
    execution_policy: {
      allowed: true,
      blocking_count: 0,
      message: '单节点复跑控制项已满足，可以进入执行确认。',
      missing_control_count: 0,
      mode: 'single_node_rerun_ready',
      requires_confirmation: true,
      side_effect_policy: sideEffectPolicy,
    },
    full_run_request: {
      scheduled_job_id: 'scheduled_job_weekly_feedback',
      source_run_id: 'scheduled_job_run_weekly_feedback',
      trigger_type: 'manual_rerun',
    },
    missing_controls: [],
    next_actions: [
      {
        description: '节点 input/output/error 快照可用于排障和复制给 AI 分析。',
        key: 'inspect_node_snapshot',
        label: '查看节点快照',
        status: 'available',
      },
      {
        description: '所有必需控制项已满足，可进入单节点执行确认。',
        key: 'confirm_single_node_rerun',
        label: '确认单节点复跑',
        status: 'available',
      },
    ],
    node_id: nodeId,
    preflight_status: 'ready',
    rerun_plan: {
      safe_next_action: safeNextAction,
      side_effect_policy: sideEffectPolicy,
      single_node_supported: true,
    },
    rerun_controls: controls,
    rerun_supported: true,
    run_id: 'scheduled_job_run_weekly_feedback',
    safe_next_action: safeNextAction,
    side_effect_policy: sideEffectPolicy,
    snapshot_preview: snapshotPreview,
    snapshot_status: { error: false, input: true, output: true },
    stage,
    stage_label: stageLabel,
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
          generic_result_actions: [
            { label: '仅保存运行结果', value: 'save_scheduled_job_result' },
            { label: '创建需求', value: 'create_requirements' },
            { label: '同步钉钉文档', value: 'sync_dingtalk_document' },
            { label: '发送通知记录', value: 'send_notification' },
          ],
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
    if (
      typeof input === 'string'
      && input.startsWith('/api/system/ai-executor-runners')
      && init?.method === 'GET'
    ) {
      return jsonResponse({
        data: {
          items: [
            {
              executor_types: ['model_gateway'],
              health_status: 'managed',
              id: 'ai_executor_runner_system_default',
              name: '系统默认执行器',
              protocol: 'model_gateway',
              status: 'active',
              workspace_roots: ['*'],
            },
            {
              executor_types: ['codex'],
              health_status: 'online',
              id: 'ai_executor_runner_codex',
              name: '本地 Codex 执行器',
              protocol: 'runner_polling',
              status: 'active',
              workspace_roots: ['/Users/zeek/source/e-ai-brain'],
            },
          ],
          total: 1,
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
                config_json: {
                  scan_mode: 'native_full_scan',
                  scan_rules: ['secrets', 'internal_addresses'],
                },
                cron_expression: '0 2 * * MON',
                enabled: true,
                execution_mode: 'ai_assisted',
                job_type: 'code_repository_inspection',
                knowledge_document_ids: [],
                name: '代码仓库质量安全规范巡检',
                result_actions: [
                  { type: 'write_code_inspection_report' },
                  { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
                  { channels: ['email'], recipients: [], type: 'send_notification' },
                ],
                schedule_type: 'cron',
                skill_ids: [],
                source_system: 'code-inspection',
              },
              resource_selectors: {
                agent: {
                  code_candidates: ['code-reviewer'],
                  fallback_code_candidates: ['code_reviewer', 'code_inspection_agent'],
                  text_candidates: ['代码审查', '代码巡检', 'code review', 'code inspection'],
                },
                model_gateway_config: { strategy: 'default_or_first_active' },
                plugin_action: {
                  code_candidates: ['scan_github_code_inspection', 'scan_gitlab_code_inspection'],
                  text_candidates: ['code_inspection', '代码巡检'],
                },
                skill: {
                  code_candidates: ['code_analysis_skill'],
                  fallback_code_candidates: ['code_inspection_analysis', 'code_review'],
                  text_candidates: ['代码分析skill', '代码分析', '代码巡检', '代码审查', 'code inspection', 'code review'],
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
      if (options.dryRunResponse !== undefined) {
        const data = typeof options.dryRunResponse === 'function'
          ? await options.dryRunResponse(body)
          : options.dryRunResponse;
        return jsonResponse({ data });
      }
      const sampleReuse = typeof body.config_json?.sample_reuse === 'object' && body.config_json.sample_reuse
        ? body.config_json.sample_reuse
        : {};
      const sampleSource = typeof sampleReuse.sample_source === 'string'
        ? sampleReuse.sample_source
        : 'live_dry_run_response';
      return jsonResponse({
        data: {
          job_type: body.job_type,
          sample_reuse: {
            action_preview_ready: true,
            data_connection_sample: {
              records_imported: 18,
              response_available: true,
              source: sampleSource,
              status: 'ready',
            },
            output_preview_ready: true,
            preferred_action_preview_source: 'skill_output_schema',
            reusable_steps: [
              { key: 'data_connection_sample', label: '复用数据连接样例', source: sampleSource, status: 'ready' },
              { key: 'action_write_preview', label: '预览动作写入', source: 'skill_output_schema', status: 'ready' },
              { key: 'scheduled_job_config', label: '保存为定时作业配置', source: 'current_dry_run_payload', status: 'ready' },
            ],
              reuse_wizard: {
                can_continue: true,
                current_step_label: '全链路试运行',
                current_step: 'scheduled_job_dry_run',
                blocked_steps: 0,
                completed_steps: 4,
                handoff_summary: [
                  { key: 'data_connection_sample', label: '数据连接样例', source: sampleSource, status: 'ready' },
                  { key: 'ai_output_preview', label: 'AI 输出预览', source: 'skill_output_schema', status: 'ready' },
                  { key: 'action_write_preview', label: '动作写入预览', source: 'skill_output_schema', status: 'ready' },
                  { key: 'job_config', label: '作业配置', source: 'current_dry_run_payload', status: 'ready' },
                ],
                missing_requirements: [],
                next_action: 'save_scheduled_job',
                next_action_description: '保存当前配置为定时作业，后续运行记录将继续展示三段核心节点。',
                pending_steps: 0,
                primary_action_label: '保存为定时作业',
                progress_label: '4/4 步已就绪',
                progress_percent: 100,
                sample_source: sampleSource,
                status: 'ready',
                steps: [
                { key: 'connection_test', label: '数据连接样例', source: sampleSource, status: 'succeeded' },
                { key: 'ai_processing_preview', label: 'AI 处理预览', source: 'skill_output_schema', status: 'succeeded' },
                { key: 'action_trial', label: '动作写入预览', source: 'skill_output_schema', status: 'succeeded' },
                  { key: 'scheduled_job_config', label: '生成作业配置', source: 'current_dry_run_payload', status: 'ready' },
                ],
                total_steps: 4,
              },
          },
          stages: {
            ai_processing: {
              mapping_contract: {
                checked_paths: [
                  { field: 'insights_path', path: '$.insights', supported: true },
                ],
                invalid_fields: [],
                status: 'succeeded',
              },
              mapping_status: 'succeeded',
              output_preview: { insights: [{ title: '洞察样例' }] },
              output_preview_source: 'skill_output_schema',
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
                action_name: '写入用户洞察表',
                write_preview: { candidate_count: 1, records_imported: 1, write_target_label: '用户洞察表' },
                write_preview_source: 'skill_output_schema',
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
      input === '/api/system/scheduled-job-runs/scheduled_job_run_weekly_feedback/trace-nodes/data_connection/rerun-preview'
      && init?.method === 'GET'
    ) {
      return jsonResponse({
        data: {
          blocked_by: [],
          can_preview_from_snapshot: true,
          control_summary: {
            blocked_count: 0,
            missing_count: 0,
            needs_review_count: 0,
            satisfied_count: 3,
            status_counts: { satisfied: 3 },
            total: 3,
          },
          debug_actions: [],
          execution_policy: {
            allowed: true,
            blocking_count: 0,
            message: '单节点复跑控制项已满足，可以进入执行确认。',
            missing_control_count: 0,
            mode: 'single_node_ready',
            requires_confirmation: true,
            side_effect_policy: 'external_read_or_fetch',
          },
          full_run_request: {
            scheduled_job_id: 'scheduled_job_weekly_feedback',
            source_run_id: 'scheduled_job_run_weekly_feedback',
            trigger_type: 'manual_rerun',
          },
          missing_controls: [],
          node_id: 'data_connection',
          next_actions: [
            {
              description: '节点 input/output/error 快照可用于排障和复制给 AI 分析。',
              key: 'inspect_node_snapshot',
              label: '查看节点快照',
              status: 'available',
            },
            {
              description: '所有必需控制项已满足，可进入单节点执行确认。',
              key: 'confirm_single_node_rerun',
              label: '确认单节点复跑',
              status: 'available',
            },
          ],
          preflight_status: 'ready',
          rerun_plan: {
            safe_next_action: 'confirm_single_node_rerun',
            side_effect_policy: 'external_read_or_fetch',
            single_node_supported: true,
          },
          rerun_controls: [
            {
              key: 'request_snapshot',
              label: '请求快照',
              reason: '已有可用于预检的节点快照',
              required: true,
              satisfied: true,
              status: 'satisfied',
            },
            {
              key: 'connection_read_idempotency',
              label: '连接读取幂等',
              reason: '已使用原插件调用日志生成连接读取幂等键',
              required: true,
              satisfied: true,
              status: 'satisfied',
            },
            {
              key: 'downstream_ai_and_action_invalidation',
              label: '下游 AI/动作失效策略',
              reason: '单节点复跑会生成独立运行记录，下游 AI 和动作不执行',
              required: true,
              satisfied: true,
              status: 'satisfied',
            },
          ],
          rerun_supported: true,
          run_id: 'scheduled_job_run_weekly_feedback',
          safe_next_action: 'confirm_single_node_rerun',
          side_effect_policy: 'external_read_or_fetch',
          snapshot_preview: {
            error: { available: false, size_bytes: 0, truncated: false, value: null },
            input: {
              available: true,
              size_bytes: 25,
              truncated: false,
              value: { week_start: '20260601' },
            },
            output: {
              available: true,
              size_bytes: 51,
              truncated: false,
              value: { records_imported: 18, response_status_code: 200 },
            },
          },
          snapshot_status: { error: false, input: true, output: true },
          stage: 'data_connection',
          stage_label: '数据连接',
        },
      });
    }
    if (
      input === '/api/system/scheduled-job-runs/scheduled_job_run_weekly_feedback/trace-nodes/skill_processing/rerun-preview'
      && init?.method === 'GET'
    ) {
      if (traceNodeRerunMode === 'ready_all') {
        return jsonResponse({
          data: readyTraceNodeRerunPreview({
            controls: [
              {
                key: 'input_snapshot',
                label: '输入快照',
                reason: '已有可复用的数据连接响应快照',
                required: true,
                satisfied: true,
                status: 'satisfied',
              },
              {
                key: 'model_gateway_idempotency',
                label: '模型幂等',
                reason: '已使用来源运行和节点 ID 生成模型调用幂等键',
                required: true,
                satisfied: true,
                status: 'satisfied',
              },
              {
                key: 'downstream_action_invalidation',
                label: '下游动作失效策略',
                reason: '单节点复跑会生成独立运行记录，下游动作不执行',
                required: true,
                satisfied: true,
                status: 'satisfied',
              },
            ],
            nodeId: 'skill_processing',
            sideEffectPolicy: 'model_gateway_call',
            snapshotPreview: {
              error: { available: false, size_bytes: 0, truncated: false, value: null },
              input: { available: true, size_bytes: 24, truncated: false, value: { source_row_count: 18 } },
              output: { available: true, size_bytes: 21, truncated: false, value: { candidate_count: 1 } },
            },
            stage: 'ai_processing',
            stageLabel: 'AI执行',
          }),
        });
      }
      return jsonResponse({
        data: {
          blocked_by: ['single_node_rerun_execution_guarded'],
          can_preview_from_snapshot: true,
          control_summary: {
            blocked_count: 1,
            missing_count: 0,
            needs_review_count: 1,
            satisfied_count: 1,
            total: 3,
          },
          execution_policy: {
            allowed: false,
            blocking_count: 1,
            message: '该节点的单节点复跑控制项未全部满足，当前以节点快照预检和整条运行记录复跑作为安全替代。',
            missing_control_count: 0,
            mode: 'protected_preview_only',
            requires_confirmation: true,
            side_effect_policy: 'model_gateway_call',
          },
          full_run_request: {
            scheduled_job_id: 'scheduled_job_weekly_feedback',
            source_run_id: 'scheduled_job_run_weekly_feedback',
            trigger_type: 'manual_rerun',
          },
          missing_controls: [],
          next_actions: [
            {
              description: '节点 input/output/error 快照可用于排障和复制给 AI 分析。',
              key: 'inspect_node_snapshot',
              label: '查看节点快照',
              status: 'available',
            },
            {
              description: '重新执行完整作业链路，保留上下游一致性和副作用保护。',
              key: 'rerun_full_scheduled_job',
              label: '复跑整条运行记录',
              request: {
                scheduled_job_id: 'scheduled_job_weekly_feedback',
                source_run_id: 'scheduled_job_run_weekly_feedback',
                trigger_type: 'manual_rerun',
              },
              status: 'recommended',
            },
            {
              description: '该节点可能产生模型成本，需额外确认。',
              key: 'review_side_effect_policy',
              label: '确认副作用策略',
              side_effect_policy: 'model_gateway_call',
              status: 'needs_review',
            },
          ],
          node_id: 'skill_processing',
          preflight_status: 'blocked',
          rerun_controls: [
            {
              key: 'input_snapshot',
              label: '输入快照',
              reason: '已有 AI 处理输入快照',
              required: true,
              satisfied: true,
              status: 'satisfied',
            },
            {
              key: 'model_gateway_idempotency',
              label: '模型幂等',
              reason: '模型调用副作用需保护',
              required: true,
              satisfied: false,
              status: 'needs_review',
            },
          ],
          rerun_supported: false,
          run_id: 'scheduled_job_run_weekly_feedback',
          safe_next_action: 'rerun_full_scheduled_job',
          side_effect_policy: 'model_gateway_call',
          snapshot_preview: {
            error: { available: false, size_bytes: 0, truncated: false, value: null },
            input: { available: true, size_bytes: 24, truncated: false, value: { source_row_count: 18 } },
            output: { available: true, size_bytes: 21, truncated: false, value: { candidate_count: 1 } },
          },
          snapshot_status: { error: false, input: true, output: true },
          stage: 'ai_processing',
          stage_label: 'AI执行',
        },
      });
    }
    if (
      input === '/api/system/scheduled-job-runs/scheduled_job_run_weekly_feedback/trace-nodes/result_action/rerun-preview'
      && init?.method === 'GET'
    ) {
      return jsonResponse({
        data: readyTraceNodeRerunPreview({
          controls: [
            {
              key: 'action_input_snapshot',
              label: '动作输入快照',
              reason: '已有 AI 输出快照可作为动作输入',
              required: true,
              satisfied: true,
              status: 'satisfied',
            },
            {
              key: 'write_idempotency',
              label: '写入幂等',
              reason: '已使用来源运行、节点和写入目标生成幂等键',
              required: true,
              satisfied: true,
              status: 'satisfied',
            },
            {
              key: 'side_effect_guard',
              label: '副作用防重',
              reason: '结果动作复跑会生成新的写入记录并保留来源运行引用',
              required: true,
              satisfied: true,
              status: 'satisfied',
            },
          ],
          nodeId: 'result_action',
          sideEffectPolicy: 'idempotent_result_write',
          snapshotPreview: {
            error: { available: false, size_bytes: 0, truncated: false, value: null },
            input: { available: true, size_bytes: 35, truncated: false, value: { write_target: 'user_feedback_insights' } },
            output: { available: true, size_bytes: 31, truncated: false, value: { created_ids: ['insight_001'] } },
          },
          stage: 'result_action',
          stageLabel: '动作',
        }),
      });
    }
    if (
      input === '/api/system/scheduled-job-runs/scheduled_job_run_weekly_feedback/trace-nodes/data_connection/rerun'
      && init?.method === 'POST'
    ) {
      traceNodeRerunCalls.push('data_connection');
      return jsonResponse({
        data: {
          config_snapshot: {
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            model_gateway_config_id: 'model_gateway_scheduled',
            skill_ids: ['skill_feedback'],
          },
          id: 'scheduled_job_run_weekly_feedback_data_connection_rerun',
          records_imported: 18,
          result_summary: {
            execution_nodes: {
              data_connection: {
                note: '单节点复跑仅重新执行数据连接，下游 AI 和动作未执行。',
                records_imported: 18,
                status: 'succeeded',
              },
              result_action: { status: 'skipped' },
              skill_processing: { model_gateway_called: false, status: 'skipped' },
            },
            message: 'Trace DAG 数据连接节点单节点复跑完成',
            trace_node_rerun: {
              mode: 'single_node_data_connection',
              node_id: 'data_connection',
              source_run_id: 'scheduled_job_run_weekly_feedback',
            },
          },
          scheduled_job_id: 'scheduled_job_weekly_feedback',
          source_run_id: 'scheduled_job_run_weekly_feedback',
          status: 'succeeded',
          trigger_type: 'manual_rerun',
        },
      });
    }
    if (
      input === '/api/system/scheduled-job-runs/scheduled_job_run_weekly_feedback/trace-nodes/skill_processing/rerun'
      && init?.method === 'POST'
    ) {
      traceNodeRerunCalls.push('skill_processing');
      return jsonResponse({
        data: {
          config_snapshot: {
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            model_gateway_config_id: 'model_gateway_scheduled',
            skill_ids: ['skill_feedback'],
          },
          id: 'scheduled_job_run_weekly_feedback_skill_processing_rerun',
          records_imported: 1,
          result_summary: {
            execution_nodes: {
              data_connection: { note: '单节点复跑复用来源运行数据连接响应快照。', status: 'reused_snapshot' },
              result_action: { status: 'skipped' },
              skill_processing: {
                model_gateway_called: true,
                note: '单节点复跑仅重新执行 AI 处理，下游动作未执行。',
                output: { candidate_count: 1 },
                status: 'succeeded',
              },
            },
            message: 'Trace DAG AI 处理节点单节点复跑完成',
            trace_node_rerun: {
              mode: 'single_node_skill_processing',
              node_id: 'skill_processing',
              source_run_id: 'scheduled_job_run_weekly_feedback',
            },
          },
          scheduled_job_id: 'scheduled_job_weekly_feedback',
          source_run_id: 'scheduled_job_run_weekly_feedback',
          status: 'succeeded',
          trigger_type: 'manual_rerun',
        },
      });
    }
    if (
      input === '/api/system/scheduled-job-runs/scheduled_job_run_weekly_feedback/trace-nodes/result_action/rerun'
      && init?.method === 'POST'
    ) {
      traceNodeRerunCalls.push('result_action');
      return jsonResponse({
        data: {
          config_snapshot: {
            execution_mode: 'ai_generated',
            job_type: 'user_feedback_insight_extract',
            model_gateway_config_id: 'model_gateway_scheduled',
            skill_ids: ['skill_feedback'],
          },
          id: 'scheduled_job_run_weekly_feedback_result_action_rerun',
          records_imported: 1,
          result_summary: {
            execution_nodes: {
              data_connection: { status: 'not_run' },
              result_action: {
                created_ids: ['insight_001'],
                note: '单节点复跑仅执行结果动作，数据连接和 AI 处理未重新执行。',
                records_imported: 1,
                status: 'succeeded',
                write_target: 'user_feedback_insights',
              },
              skill_processing: { status: 'reused_snapshot' },
            },
            message: 'Trace DAG 结果动作节点单节点复跑完成',
            trace_node_rerun: {
              mode: 'single_node_result_action',
              node_id: 'result_action',
              source_run_id: 'scheduled_job_run_weekly_feedback',
            },
          },
          scheduled_job_id: 'scheduled_job_weekly_feedback',
          source_run_id: 'scheduled_job_run_weekly_feedback',
          status: 'succeeded',
          trigger_type: 'manual_rerun',
        },
      });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/system/scheduled-job-runs')
      && init?.method === 'GET'
    ) {
      runListCalls.push(input);
      runListCallCount += 1;
      if (options.deferRunListReload && runListCallCount > 1) {
        return new Promise<Response>(() => undefined);
      }
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
              action_type: 'mcp_tool',
              code: 'update_dingtalk_document_content',
              id: 'plugin_action_dingtalk_update',
              name: '钉钉文档 - 更新内容',
              plugin_id: 'plugin_dingtalk',
              result_mapping: { write_target: 'dingtalk_document' },
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
          total: 2,
        },
      });
    }
    if (input === '/api/system/ai-agents' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            { code: 'insight_agent', id: 'agent_insight', name: '洞察 Agent', status: 'active' },
            { code: 'code_reviewer', id: 'agent_legacy_code_reviewer', name: '旧代码审查角色', status: 'active' },
            { code: 'code-reviewer', id: 'agent_code_reviewer', name: '代码审查角色', status: 'active' },
          ],
          total: 3,
        },
      });
    }
    if (input === '/api/system/ai-skills' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            { code: 'weekly_feedback_analysis', id: 'skill_feedback', name: '每周反馈分析', status: 'active' },
            { code: 'code_inspection_analysis', id: 'skill_legacy_code_inspection', name: '代码巡检分析', status: 'active' },
            { code: 'code_analysis_skill', id: 'skill_code_inspection', name: '代码分析skill', status: 'active' },
          ],
          total: 3,
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
    traceNodeRerunCalls,
  };
}

function buildReadyTraceNodeRerunRun(): Record<string, unknown> {
  const commonRerunPlan = {
    safe_next_action: 'confirm_single_node_rerun',
    single_node_supported: true,
    snapshot_status: { error: false, input: true, output: true },
  };
  return {
    config_snapshot: {
      execution_mode: 'ai_generated',
      job_type: 'user_feedback_insight_extract',
      model_gateway_config_id: 'model_gateway_scheduled',
      skill_ids: ['skill_feedback'],
    },
    finished_at: '2026-06-11T10:00:03Z',
    id: 'scheduled_job_run_weekly_feedback',
    records_imported: 1,
    result_summary: {
      execution_nodes: {
        data_connection: { records_imported: 18, status: 'succeeded' },
        result_action: {
          created_ids: ['insight_001'],
          records_imported: 1,
          status: 'succeeded',
          write_target: 'user_feedback_insights',
        },
        skill_processing: {
          model_gateway_called: true,
          output: { candidate_count: 1 },
          status: 'succeeded',
        },
      },
      trace_graph: {
        edges: [
          { from: 'data_connection', to: 'skill_processing' },
          { from: 'skill_processing', to: 'result_action' },
        ],
        nodes: [
          {
            duration_ms: 318,
            id: 'data_connection',
            input: { week_start: '20260601' },
            label: '数据连接获取内容',
            output: { records_imported: 18 },
            retry_count: 0,
            stage: 'data_connection',
            stage_label: '数据连接',
            status: 'succeeded',
          },
          {
            debug_actions: [{ enabled: true, label: '复制复跑计划', type: 'copy_rerun_plan' }],
            duration_ms: 860,
            id: 'skill_processing',
            input: { source_row_count: 18 },
            label: '经过 Skill 处理后的内容',
            output: { candidate_count: 1 },
            rerun_hint: 'AI 处理节点可在控制项满足时单独复跑。',
            rerun_plan: {
              ...commonRerunPlan,
              downstream_invalidation_strategy: 'isolated_single_node_run',
              side_effect_policy: 'model_gateway_call',
            },
            rerun_supported: true,
            retry_count: 0,
            snapshot_status: { error: false, input: true, output: true },
            stage: 'ai_processing',
            stage_label: 'AI执行',
            status: 'succeeded',
          },
          {
            debug_actions: [{ enabled: true, label: '复制复跑计划', type: 'copy_rerun_plan' }],
            duration_ms: 42,
            id: 'result_action',
            input: { write_target: 'user_feedback_insights' },
            label: '结果写入反馈内容',
            output: { created_ids: ['insight_001'] },
            rerun_hint: '结果动作节点可在写入幂等满足时单独复跑。',
            rerun_plan: {
              ...commonRerunPlan,
              downstream_invalidation_strategy: 'isolated_single_node_run',
              side_effect_policy: 'idempotent_result_write',
            },
            rerun_supported: true,
            retry_count: 0,
            snapshot_status: { error: false, input: true, output: true },
            stage: 'result_action',
            stage_label: '动作',
            status: 'succeeded',
          },
        ],
      },
    },
    scheduled_job_id: 'scheduled_job_weekly_feedback',
    started_at: '2026-06-11T10:00:00Z',
    status: 'succeeded',
    trigger_type: 'manual',
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
    const { jobListCalls, runListCalls } = installScheduledJobsFetchMock({
      runs: [
        {
          id: 'scheduled_job_run_weekly_feedback',
          scheduled_job_id: 'scheduled_job_weekly_feedback',
          scheduled_job_name: '每周用户反馈洞察抽取',
          status: 'succeeded',
          trigger_type: 'manual',
        },
      ],
    });

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

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    expect(await screen.findByText('作业名称')).toBeInTheDocument();
    expect(screen.getByText('每周用户反馈洞察抽取')).toBeInTheDocument();
    expect(screen.queryByText('作业 ID')).not.toBeInTheDocument();
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
    expect(within(dialog).getByLabelText('取数连接')).toBeInTheDocument();
    expect(within(dialog).getByText('用于用户反馈、AI 客服聊天记录、HTTP API 等直接取数连接，可选择多个同类连接')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('执行链路')).toHaveTextContent('数据来源 → AI执行 → 动作 → 运行记录');
    expect(within(dialog).getByLabelText('数据来源')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('AI执行配置')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('AI执行')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('AI执行器')).toBeInTheDocument();
    fireEvent.mouseDown(within(dialog).getByLabelText('AI执行器'));
    fireEvent.click(await screen.findByText(/本地 Codex 执行器/));
    await waitFor(() => expect(within(dialog).getByLabelText('工作区')).toBeInTheDocument());
    expect(within(dialog).getByDisplayValue('/Users/zeek/source/e-ai-brain')).toBeInTheDocument();
    expect(within(dialog).getByText('Runner 完成后会自动回写任务运行结果，并继续执行后续动作。')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('AI 模型')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('AI角色')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Skills')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('知识引用')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('结果动作')).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: /新增结果动作/ })).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: /新增钉钉文档更新/ })).toBeInTheDocument();
    expect(within(dialog).queryByText('当前作业使用数据来源动作的结果映射生成写入反馈')).not.toBeInTheDocument();
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

    expect(await within(dialog).findByText('默认扫描该产品下 1 个 active 代码仓库')).toBeInTheDocument();
    expect(within(dialog).queryByLabelText('代码仓库')).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: '高级仓库配置' }));
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
    expect(within(dialog).getByText('执行链路：数据来源 → AI执行 → 动作 → 运行记录')).toBeInTheDocument();

    expect(within(dialog).getByLabelText('编排节点 数据来源')).toHaveTextContent('待配置');
    expect(within(dialog).getByLabelText('编排节点 AI执行')).toHaveTextContent('待配置');
    expect(within(dialog).getByLabelText('编排节点 知识引用')).toHaveTextContent('可选');
    expect(within(dialog).getByLabelText('编排节点 动作')).toHaveTextContent('待配置');

    fireEvent.mouseDown(within(dialog).getByLabelText('作业模板'));
    expect(await screen.findByText('邮件摘要收取')).toBeInTheDocument();
    expect(screen.getByText('GitLab MR AI 审查')).toBeInTheDocument();
    expect(screen.getByText('AI 执行器仓库任务')).toBeInTheDocument();
    fireEvent.click(await screen.findByText('每周用户反馈洞察抽取'));

    await waitFor(() =>
      expect(within(dialog).getByLabelText('编排节点 数据来源')).toHaveTextContent('已配置'),
    );
    expect(within(dialog).getByLabelText('编排节点 数据来源')).toHaveTextContent('生产 MaxCompute 项目');
    expect(within(dialog).getByLabelText('编排节点 AI执行')).toHaveTextContent('已配置');
    expect(within(dialog).getByLabelText('编排节点 AI执行')).toHaveTextContent('定时作业模型');
    expect(within(dialog).getByLabelText('编排节点 知识引用')).toHaveTextContent('已选择');
    expect(within(dialog).getByLabelText('编排节点 动作')).toHaveTextContent('已配置');
    expect(within(dialog).getByLabelText('编排节点 动作')).toHaveTextContent('获取本周用户反馈数据');

    fireEvent.click(within(dialog).getByRole('button', { name: '测试数据来源' }));

    await waitFor(() => expect(connectionTestIds).toEqual(['connection_maxcompute_prod']));
    expect(within(dialog).getByLabelText('编排节点 数据来源')).toHaveTextContent('连接测试 succeeded');
    expect(within(dialog).getByLabelText('编排节点 数据来源')).toHaveTextContent('128ms');
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
    expect(within(dryRunResult).getByLabelText('样例复用摘要')).toHaveTextContent('数据样例 可复用');
    expect(within(dryRunResult).getByLabelText('样例复用摘要')).toHaveTextContent('样例行数 18');
    expect(within(dryRunResult).getByLabelText('样例复用摘要')).toHaveTextContent('进度：4/4 步已就绪');
    expect(within(dryRunResult).getByLabelText('样例复用摘要')).toHaveTextContent('当前：全链路试运行');
    expect(within(dryRunResult).getByLabelText('样例复用摘要')).toHaveTextContent('下一步：保存为定时作业');
    expect(within(dryRunResult).getByLabelText('样例复用摘要')).toHaveTextContent('数据连接样例 · ready');
    expect(within(dryRunResult).getByLabelText('样例复用摘要')).toHaveTextContent('AI 输出预览 · ready');
    expect(within(dryRunResult).getByLabelText('样例复用摘要')).toHaveTextContent('作业配置 · ready');
    expect(within(dryRunResult).getByText('AI 处理预览 · succeeded')).toBeInTheDocument();
    expect(within(dryRunResult).getByText('动作写入预览 · succeeded')).toBeInTheDocument();
    expect(within(dryRunResult).getByText('保存为定时作业配置 · ready')).toBeInTheDocument();
    expect(within(dryRunResult).getByText('数据连接预览')).toBeInTheDocument();
    expect(within(dryRunResult).getByText('AI契约校验')).toBeInTheDocument();
    expect(within(dryRunResult).getByText('结果写入预览')).toBeInTheDocument();
    expect(within(dryRunResult).getByLabelText('Skill 输出映射校验摘要')).toHaveTextContent('已校验 1 个字段');
    expect(within(dryRunResult).getByText('insights_path: $.insights 已命中')).toBeInTheDocument();
    expect(within(dryRunResult).getAllByText('Skill 输出样例').length).toBeGreaterThan(0);
    expect(within(dryRunResult).getByText(/预计写入 1 条/)).toBeInTheDocument();
    expect(within(dryRunResult).getByText(/connection_maxcompute_prod/)).toBeInTheDocument();
    expect(within(dryRunResult).getByText(/user_feedback_insights/)).toBeInTheDocument();
  });

  it('explains blocked sample reuse requirements when scheduled job dry-run cannot build previews', async () => {
    const { jobDryRunBodies } = installScheduledJobsFetchMock({
      dryRunResponse: {
        job_type: 'user_feedback_insight_extract',
        sample_reuse: {
          action_preview_ready: false,
          data_connection_sample: {
            response_available: false,
            source: 'not_available',
            status: 'missing',
          },
          output_preview_ready: false,
          preferred_action_preview_source: 'not_available',
          reusable_steps: [
            { key: 'data_connection_sample', label: '复用数据连接样例', source: 'not_available', status: 'missing' },
            { key: 'action_write_preview', label: '预览动作写入', source: 'not_available', status: 'missing' },
            { key: 'scheduled_job_config', label: '保存为定时作业配置', source: 'current_dry_run_payload', status: 'pending' },
          ],
          reuse_wizard: {
            blocked_steps: 3,
            can_continue: false,
            completed_steps: 0,
            current_step: 'scheduled_job_dry_run',
            current_step_label: '全链路试运行',
            handoff_summary: [
              { key: 'data_connection_sample', label: '数据连接样例', source: 'not_available', status: 'missing' },
              { key: 'ai_output_preview', label: 'AI 输出预览', source: 'not_available', status: 'missing' },
              { key: 'action_write_preview', label: '动作写入预览', source: 'not_available', status: 'missing' },
              { key: 'job_config', label: '作业配置', source: 'current_dry_run_payload', status: 'pending' },
            ],
            missing_requirements: [
              'data_connection_sample',
              'ai_output_preview',
              'action_write_preview',
            ],
            next_action: 'review_dry_run_issues',
            next_action_description: '先处理缺失的样例、AI 输出或动作写入预览，再保存作业。',
            pending_steps: 1,
            primary_action_label: '检查试运行问题',
            progress_label: '0/4 步已就绪',
            progress_percent: 0,
            sample_source: 'not_available',
            status: 'partial',
            steps: [
              { key: 'connection_test', label: '数据连接样例', source: 'not_available', status: 'blocked' },
              { key: 'ai_processing_preview', label: 'AI 处理预览', source: 'not_available', status: 'blocked' },
              { key: 'action_trial', label: '动作写入预览', source: 'not_available', status: 'blocked' },
              { key: 'scheduled_job_config', label: '生成作业配置', source: 'current_dry_run_payload', status: 'pending' },
            ],
            total_steps: 4,
          },
        },
        stages: {
          ai_processing: {
            mapping_contract: {
              checked_paths: [{ field: 'insights_path', path: '$.insights', supported: false }],
              invalid_fields: [{ field: 'insights_path', path: '$.insights' }],
              status: 'failed',
            },
            mapping_status: 'failed',
            output_preview_source: 'not_available',
            will_call_model_gateway: true,
          },
          data_connection: {
            connection_id: 'connection_maxcompute_prod',
            error_message: 'HTTP Error 400: Bad Request',
            status: 'failed',
          },
          result_actions: [
            {
              action_id: 'plugin_action_maxcompute',
              action_name: '写入用户洞察表',
              write_preview_source: 'not_available',
              write_target: 'user_feedback_insights',
            },
          ],
        },
        status: 'failed',
      },
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('作业模板')).toBeInTheDocument());
    fireEvent.mouseDown(within(dialog).getByLabelText('作业模板'));
    fireEvent.click(await screen.findByText('每周用户反馈洞察抽取'));

    fireEvent.click(within(dialog).getByRole('button', { name: '全链路试运行' }));

    await waitFor(() => expect(jobDryRunBodies).toHaveLength(1));
    const dryRunResult = await within(dialog).findByLabelText('全链路试运行结果');
    const sampleReuseSummary = within(dryRunResult).getByLabelText('样例复用摘要');
    expect(sampleReuseSummary).toHaveTextContent('样例复用链路暂未就绪');
    expect(sampleReuseSummary).toHaveTextContent('进度：0/4 步已就绪');
    expect(sampleReuseSummary).toHaveTextContent('下一步：检查试运行问题');
    expect(sampleReuseSummary).toHaveTextContent('阻断步骤 3');
    expect(sampleReuseSummary).toHaveTextContent('需要处理：数据连接样例、AI 输出预览、动作写入预览');
    expect(sampleReuseSummary).toHaveTextContent('先处理缺失的样例、AI 输出或动作写入预览，再保存作业。');
    expect(sampleReuseSummary).toHaveTextContent('数据连接样例 · blocked');
    expect(sampleReuseSummary).toHaveTextContent('AI 处理预览 · blocked');
    expect(sampleReuseSummary).toHaveTextContent('动作写入预览 · blocked');
    expect(within(dryRunResult).getByLabelText('Skill 输出映射校验摘要')).toHaveTextContent('异常 1 个');
  });

  it('shows data connection options by name without submitting environment metadata', async () => {
    const { jobCreateBodies } = installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    fireEvent.mouseDown(within(dialog).getByLabelText('取数连接'));

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

    fireEvent.mouseDown(within(feedbackDialog).getByLabelText('取数连接'));
    fireEvent.click(await screen.findByText('备用 MaxCompute 项目'));

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
        plugin_action_ids: ['plugin_action_maxcompute'],
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
    expect(within(codeDialog).getByText('AI 辅助')).toBeInTheDocument();
    expect(within(codeDialog).getByText('代码审查角色 (code-reviewer)')).toBeInTheDocument();
    expect(within(codeDialog).queryByText('请选择 Skills')).not.toBeInTheDocument();
    expect(within(codeDialog).getByDisplayValue('0 2 * * MON')).toBeInTheDocument();
    expect(within(codeDialog).getByDisplayValue('code-inspection')).toBeInTheDocument();
    expect(await within(codeDialog).findByText('默认扫描该产品下 1 个 active 代码仓库')).toBeInTheDocument();
    expect(within(codeDialog).queryByLabelText('代码仓库')).not.toBeInTheDocument();
    fireEvent.click(within(codeDialog).getByRole('button', { name: '高级仓库配置' }));
    expect(within(codeDialog).getByLabelText('代码仓库')).toBeInTheDocument();

    fireEvent.click(within(codeDialog).getByRole('button', { name: /OK|确\s*定/ }));
    await waitFor(() =>
      expect(jobCreateBodies[1]).toMatchObject({
        cron_expression: '0 2 * * MON',
        enabled: true,
        execution_mode: 'ai_assisted',
        job_type: 'code_repository_inspection',
        model_gateway_config_id: 'model_gateway_scheduled_job',
        name: '代码仓库质量安全规范巡检',
        agent_id: 'agent_code_reviewer',
        config_json: {
          scan_mode: 'native_full_scan',
          scan_rules: ['secrets', 'internal_addresses'],
        },
        product_id: 'product_ai_brain',
        result_actions: [
          { type: 'write_code_inspection_report' },
          { severity_threshold: 'critical', type: 'create_bug_for_severe_findings' },
          { channels: ['email'], recipients: [], type: 'send_notification' },
        ],
        schedule_type: 'cron',
        skill_ids: ['skill_code_inspection'],
        source_system: 'code-inspection',
      }),
    );
    expect(jobCreateBodies[1]).not.toHaveProperty('connection_environment');
    expect(jobCreateBodies[1]).toMatchObject({
      plugin_action_id: null,
      plugin_action_ids: [],
      plugin_connection_id: 'connection_github_prod',
      plugin_connection_ids: ['connection_github_prod'],
    });
    expect(jobCreateBodies[1]).toEqual(
      expect.objectContaining({
        config_json: expect.not.objectContaining({
          branch: expect.anything(),
          repository_id: expect.anything(),
          repository_ids: expect.anything(),
        }),
      }),
    );

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

  it('configures DingTalk document updates as a result action for weekly feedback insights', async () => {
    installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    fireEvent.mouseDown(within(dialog).getByLabelText('作业模板'));
    fireEvent.click(await screen.findByText('每周用户反馈洞察抽取'));

    fireEvent.click(within(dialog).getByRole('button', { name: /新增钉钉文档更新/ }));

    const dingtalkActionSelect = await within(dialog).findByText('钉钉文档 - 更新内容');
    expect(dingtalkActionSelect).toBeInTheDocument();
    expect(await within(dialog).findByPlaceholderText('钉钉文档链接或 ID')).toBeInTheDocument();
    fireEvent.mouseDown(dingtalkActionSelect);
    expect(await screen.findByText('钉钉文档 - 更新内容 (update_dingtalk_document_content)')).toBeInTheDocument();
  });

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

  it('opens an action trial scheduled job draft with sample reuse guidance', async () => {
    const { jobDryRunBodies } = installScheduledJobsFetchMock();
    const storageKey = assistantScopedStorageKey(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY);
    window.sessionStorage.setItem(
      storageKey,
      JSON.stringify({
        auto_dry_run: true,
        payload: {
          config_json: {
            sample_reuse: {
              auto_dry_run: true,
              action_id: 'plugin_action_maxcompute',
              connection_id: 'connection_maxcompute_prod',
              response_summary: {
                json: {
                  rows: [{ feedback_id: 'fb_001', content: '支付体验很好' }],
                },
                status_code: 200,
              },
              reuse_wizard: {
                can_continue: true,
                current_step: 'action_trial',
                current_step_label: '动作写入预览',
                blocked_steps: 0,
                completed_steps: 4,
                handoff_summary: [
                  { key: 'response_sample', label: '响应样例', source: 'connection_test_response', status: 'ready' },
                  { key: 'input_mapping', label: '连接输入映射', source: 'trial_input_payload', status: 'ready' },
                  { key: 'output_mapping', label: '结果映射', source: 'plugin_action_result_mapping', status: 'ready' },
                  { key: 'write_preview', label: '写入预览', source: 'connection_test_response', status: 'ready' },
                ],
                missing_requirements: [],
                next_action: 'create_scheduled_job_draft',
                next_action_description: '生成定时作业草稿，并带入连接、动作、映射、响应样例和写入预览。',
                pending_steps: 0,
                primary_action_label: '生成定时作业草稿',
                progress_label: '4/4 步已就绪',
                progress_percent: 100,
                sample_source: 'connection_test_response',
                status: 'ready',
                total_steps: 4,
              },
              sample_source: 'connection_test_response',
              write_preview: {
                records_imported: 8,
                write_target: 'scheduled_job_result',
                write_target_label: '定时作业结果',
              },
            },
          },
          enabled: true,
          execution_mode: 'deterministic',
          job_type: 'plugin_action_invoke',
          name: '调用反馈 API 定时作业',
          plugin_action_id: 'plugin_action_maxcompute',
          plugin_action_ids: ['plugin_action_maxcompute'],
          plugin_connection_id: 'connection_maxcompute_prod',
          plugin_connection_ids: ['connection_maxcompute_prod'],
          plugin_input_mapping: {},
          plugin_output_mapping: { write_target: 'scheduled_job_result' },
          product_id: 'product_ai_brain',
          schedule_type: 'manual',
          source_system: 'plugin-action-trial',
        },
        title: '从动作试运行创建：调用反馈 API',
      }),
    );

    render(<ScheduledJobsPage />);

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    expect(window.sessionStorage.getItem(storageKey)).toBeNull();
    const sampleReuseSummary = within(dialog).getByLabelText('动作试运行样例');
    expect(sampleReuseSummary).toHaveTextContent('已载入动作试运行样例');
    expect(sampleReuseSummary).toHaveTextContent('生产 MaxCompute 项目');
    expect(sampleReuseSummary).toHaveTextContent('获取本周用户反馈数据');
    expect(sampleReuseSummary).toHaveTextContent('连接测试响应样例');
    expect(sampleReuseSummary).toHaveTextContent('定时作业结果');
    expect(sampleReuseSummary).toHaveTextContent('预计写入 8');
    expect(sampleReuseSummary).toHaveTextContent('打开后自动试运行');
    expect(sampleReuseSummary).toHaveTextContent('进度：4/4 步已就绪');
    expect(sampleReuseSummary).toHaveTextContent('当前：动作写入预览');
    expect(sampleReuseSummary).toHaveTextContent('下一步：生成定时作业草稿');
    expect(sampleReuseSummary).toHaveTextContent('连接输入映射 · ready');
    expect(sampleReuseSummary).toHaveTextContent('写入预览 · ready');
    expect(within(dialog).getByLabelText('名称')).toHaveValue('调用反馈 API 定时作业');

    await waitFor(() =>
      expect(jobDryRunBodies[0]).toMatchObject({
        config_json: {
          sample_reuse: {
            auto_dry_run: true,
            action_id: 'plugin_action_maxcompute',
            connection_id: 'connection_maxcompute_prod',
            response_summary: {
              json: {
                rows: [{ feedback_id: 'fb_001', content: '支付体验很好' }],
              },
              status_code: 200,
            },
            sample_source: 'connection_test_response',
            write_preview: {
              records_imported: 8,
              write_target: 'scheduled_job_result',
              write_target_label: '定时作业结果',
            },
          },
        },
        job_type: 'plugin_action_invoke',
        plugin_action_id: 'plugin_action_maxcompute',
        plugin_connection_id: 'connection_maxcompute_prod',
        source_system: 'plugin-action-trial',
      }),
    );
    const dryRunResult = await within(dialog).findByLabelText('全链路试运行结果');
    expect(dryRunResult).toBeInTheDocument();
    expect(dryRunResult).toHaveTextContent('来源 连接测试响应样例');
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
    fireEvent.mouseDown(within(dialog).getByLabelText('取数连接'));
    fireEvent.click(await screen.findByText('生产 MaxCompute 项目'));
    fireEvent.mouseDown(within(dialog).getByLabelText('AI 模型'));
    fireEvent.click(await screen.findByText('定时作业模型 (scheduled-job-model)'));
    fireEvent.mouseDown(within(dialog).getByLabelText('AI角色'));
    fireEvent.click(await screen.findByText('洞察 Agent (insight_agent)'));
    fireEvent.mouseDown(within(dialog).getByLabelText('数据读取动作'));
    fireEvent.click(await screen.findByText('获取本周用户反馈数据'));

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() => expect(within(dialog).getByText('请选择 Skills')).toBeInTheDocument());
    expect(within(dialog).queryByText('请选择 AI 模型')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('请选择 AI角色')).not.toBeInTheDocument();
    expect(jobCreateBodies).toEqual([]);
  });

  it('defaults code inspection templates to AI-assisted processing', async () => {
    const { jobCreateBodies } = installScheduledJobsFetchMock();

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增作业' }));

    const dialog = await screen.findByRole('dialog', { name: '新增定时作业' });
    await waitFor(() => expect(within(dialog).getByLabelText('作业模板')).toBeInTheDocument());
    fireEvent.mouseDown(within(dialog).getByLabelText('作业模板'));
    fireEvent.click(await screen.findByText('代码仓库质量 / 安全 / 规范巡检'));

    expect(within(dialog).getByText('AI 辅助')).toBeInTheDocument();
    expect(within(dialog).getByText('代码审查角色 (code-reviewer)')).toBeInTheDocument();
    expect(within(dialog).queryByText('请选择 AI 模型')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('请选择 AI角色')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('请选择 Skills')).not.toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(jobCreateBodies[0]).toMatchObject({
        agent_id: 'agent_code_reviewer',
        execution_mode: 'ai_assisted',
        job_type: 'code_repository_inspection',
        model_gateway_config_id: 'model_gateway_scheduled_job',
        skill_ids: ['skill_code_inspection'],
      }),
    );
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
    expect(within(dialog).getByText('用户洞察会在 AI 分析成功后自动写入')).toBeInTheDocument();
    expect(within(dialog).queryByText('写入代码巡检报告')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('严重问题自动创建 Bug')).not.toBeInTheDocument();

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
          result_actions: [],
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

    fireEvent.mouseDown(within(dialog).getByLabelText('取数连接'));

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
    fireEvent.mouseDown(within(dialog).getByLabelText('取数连接'));
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

  it('submits native full scan mode with a selected GitHub credential connection', async () => {
    const { jobUpdateBodies } = installScheduledJobsFetchMock({
      jobs: [
        {
          config_json: {
            branch: 'main',
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
    fireEvent.mouseDown(within(dialog).getByLabelText('取数连接'));
    fireEvent.click(await screen.findByText('生产 GitHub 组织'));

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(jobUpdateBodies[0]).toMatchObject({
        config_json: {
          branch: 'main',
          orchestration: {
            plugin_action_ids: [],
            plugin_connection_ids: ['connection_github_prod'],
          },
          repository_id: 'repo_zqf',
          scan_mode: 'native_full_scan',
        },
        plugin_action_id: null,
        plugin_action_ids: [],
        plugin_connection_id: 'connection_github_prod',
        plugin_connection_ids: ['connection_github_prod'],
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
    const { runJobBodies, runJobIds, traceNodeRerunCalls } = installScheduledJobsFetchMock({
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
            package_snapshot: {
              entry: 'AGENT.md',
              runtime_boundary: {
                script_execution: 'disabled_pending_sandbox',
                script_files: ['scripts/agent_run.py'],
                script_note: 'Agent 包中的脚本目录当前不会自动执行；开启脚本执行前需要沙箱、审批和审计。',
              },
            },
            source_type: 'package',
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
              package_snapshot: {
                entry: 'SKILL.md',
                runtime_boundary: {
                  script_execution: 'disabled_pending_sandbox',
                  script_files: ['scripts/run.py'],
                  script_note: 'Skill 包中的脚本目录当前不会自动执行；开启脚本执行前需要沙箱、审批和审计。',
                },
              },
              source_type: 'package',
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
            repository_execution: {
              repo_zqf: {
                code_inspection_report: {
                  report_id: 'code_inspection_report_001',
                },
                native_scan: {
                  commit_sha: 'abc123',
                  finding_count: 2,
                  repository_id: 'repo_zqf',
                  status: 'succeeded',
                },
                result_action: {
                  feedback: { report_id: 'code_inspection_report_001' },
                  status: 'succeeded',
                },
                skill_processing: {
                  model_gateway_called: true,
                  status: 'succeeded',
                },
              },
            },
            trace_graph: {
              edges: [
                { from: 'data_connection', to: 'skill_processing' },
                { from: 'skill_processing', to: 'result_action' },
              ],
              nodes: [
                {
                  debug_actions: [
                    { enabled: true, label: '复制输入', type: 'copy_input' },
                    { enabled: true, label: '复制输出', type: 'copy_output' },
                    { enabled: true, label: '复制复跑计划', type: 'copy_rerun_plan' },
                  ],
                  duration_ms: 318,
                  error: null,
                  id: 'data_connection',
                  input: { week_start: '20260601' },
                  label: '数据连接获取内容',
                  output: { records_imported: 18, response_status_code: 200 },
                  rerun_plan: {
                    control_summary: {
                      blocked_count: 0,
                      missing_count: 0,
                      needs_review_count: 0,
                      satisfied_count: 3,
                      status_counts: { satisfied: 3 },
                      total: 3,
                    },
                    rerun_controls: [
                      {
                        key: 'request_snapshot',
                        label: '请求快照',
                        reason: '已有可用于预检的节点快照',
                        required: true,
                        satisfied: true,
                        status: 'satisfied',
                      },
                      {
                        key: 'connection_read_idempotency',
                        label: '连接读取幂等',
                        reason: '已使用原插件调用日志生成连接读取幂等键',
                        required: true,
                        satisfied: true,
                        status: 'satisfied',
                      },
                      {
                        key: 'downstream_ai_and_action_invalidation',
                        label: '下游 AI/动作失效策略',
                        reason: '单节点复跑会生成独立运行记录，下游 AI 和动作不执行',
                        required: true,
                        satisfied: true,
                        status: 'satisfied',
                      },
                    ],
                    safe_next_action: 'confirm_single_node_rerun',
                    side_effect_policy: 'external_read_or_fetch',
                    single_node_supported: true,
                    snapshot_status: { error: false, input: true, output: true },
                  },
                  rerun_hint: '如需重试该节点，请从运行记录复跑整条作业，系统会重新执行数据连接和下游节点。',
                  rerun_supported: true,
                  retry_count: 1,
                  snapshot_status: { error: false, input: true, output: true },
                  stage: 'data_connection',
                  stage_label: '数据连接',
                  status: 'succeeded',
                },
                {
                  debug_actions: [
                    { enabled: true, label: '复制输入', type: 'copy_input' },
                    { enabled: true, label: '复制输出', type: 'copy_output' },
                  ],
                  duration_ms: 860,
                  error: null,
                  id: 'skill_processing',
                  input: { source_row_count: 18 },
                  label: '经过 Skill 处理后的内容',
                  output: { candidate_count: 1 },
                  rerun_hint: '如需重试 AI 处理，请从运行记录复跑整条作业，避免跳过数据上下文和知识引用。',
                  rerun_supported: false,
                  retry_count: 1,
                  stage: 'ai_processing',
                  stage_label: 'AI执行',
                  status: 'succeeded',
                },
                {
                  debug_actions: [
                    { enabled: true, label: '复制输入', type: 'copy_input' },
                    { enabled: true, label: '复制输出', type: 'copy_output' },
                  ],
                  duration_ms: 42,
                  error: null,
                  id: 'result_action',
                  input: { write_target: 'user_feedback_insights' },
                  label: '结果写入反馈内容',
                  output: { created_ids: ['insight_001'] },
                  rerun_hint: '如需重新写入结果，请先确认目标幂等策略，再从运行记录复跑整条作业。',
                  rerun_supported: false,
                  retry_count: 1,
                  stage: 'result_action',
                  stage_label: '动作',
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
    const packageBoundary = within(dialog).getByLabelText('AI文件包运行边界');
    expect(packageBoundary).toHaveTextContent('AI角色 洞察 Agent');
    expect(packageBoundary).toHaveTextContent('入口 AGENT.md');
    expect(packageBoundary).toHaveTextContent('脚本执行 disabled_pending_sandbox');
    expect(packageBoundary).toHaveTextContent('脚本文件 scripts/agent_run.py');
    expect(packageBoundary).toHaveTextContent('Agent 包中的脚本目录当前不会自动执行');
    expect(packageBoundary).toHaveTextContent('Skill 每周反馈分析');
    expect(packageBoundary).toHaveTextContent('入口 SKILL.md');
    expect(packageBoundary).toHaveTextContent('脚本文件 scripts/run.py');
    expect(packageBoundary).toHaveTextContent('Skill 包中的脚本目录当前不会自动执行');
    const repositoryDetails = within(dialog).getByLabelText('代码仓库执行明细');
    expect(repositoryDetails).toHaveTextContent('repo_zqf');
    expect(repositoryDetails).toHaveTextContent('abc123');
    expect(repositoryDetails).toHaveTextContent('调用大模型');
    expect(repositoryDetails).toHaveTextContent('是');
    expect(repositoryDetails).toHaveTextContent('code_inspection_report_001');
    expect(within(dialog).getAllByText('数据连接获取内容').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('AI执行处理内容').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('动作反馈内容').length).toBeGreaterThan(0);
    expect(within(dialog).getByText('运行 Trace DAG')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('318ms');
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('数据连接');
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('复跑整条作业');
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('单节点复跑可用');
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('输入快照 有');
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('输出快照 有');
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('副作用 external_read_or_fetch');
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('建议 confirm_single_node_rerun');
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('复制输入');
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('复制输出');
    expect(within(dialog).getByLabelText('Trace 节点 数据连接获取内容')).toHaveTextContent('复制复跑计划');
    const dataTraceNode = within(dialog).getByLabelText('Trace 节点 数据连接获取内容');
    fireEvent.click(within(dataTraceNode).getByRole('button', { name: '复跑预检' }));
    expect(await within(dataTraceNode).findByText('节点复跑预检')).toBeInTheDocument();
    expect(
      within(dataTraceNode).getByText(
        '执行策略：单节点复跑控制项已满足，可以进入执行确认。',
      ),
    ).toBeInTheDocument();
    expect(
      within(dataTraceNode).getByText('控制项：已满足 3 / 缺失 0 / 阻断 0 / 待确认 0'),
    ).toBeInTheDocument();
    expect(within(dataTraceNode).getByText('请求快照 · satisfied')).toBeInTheDocument();
    expect(within(dataTraceNode).getByText('连接读取幂等 · satisfied')).toBeInTheDocument();
    expect(within(dataTraceNode).getByText('下游 AI/动作失效策略 · satisfied')).toBeInTheDocument();
    expect(within(dataTraceNode).getByText('下一步动作')).toBeInTheDocument();
    expect(within(dataTraceNode).getByText('查看节点快照 · available')).toBeInTheDocument();
    expect(within(dataTraceNode).getByText('确认单节点复跑 · available')).toBeInTheDocument();
    const confirmRerunButton = within(dataTraceNode).getByRole('button', { name: '确认复跑' });
    expect(confirmRerunButton).toBeInTheDocument();
    expect(within(dataTraceNode).getByText(/input: 有/)).toBeInTheDocument();
    expect(within(dataTraceNode).getByText(/output: 有/)).toBeInTheDocument();
    expect(within(dataTraceNode).getByText('error: 无')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Trace 节点 经过 Skill 处理后的内容')).toHaveTextContent('860ms');
    expect(within(dialog).getByLabelText('Trace 节点 经过 Skill 处理后的内容')).toHaveTextContent('AI执行');
    const skillTraceNode = within(dialog).getByLabelText('Trace 节点 经过 Skill 处理后的内容');
    fireEvent.click(within(skillTraceNode).getByRole('button', { name: '复跑预检' }));
    expect(await within(skillTraceNode).findByText('节点复跑预检')).toBeInTheDocument();
    expect(
      within(skillTraceNode).getByText(
        '执行策略：该节点的单节点复跑控制项未全部满足，当前以节点快照预检和整条运行记录复跑作为安全替代。',
      ),
    ).toBeInTheDocument();
    expect(within(skillTraceNode).getByText('复跑整条运行记录 · recommended')).toBeInTheDocument();
    fireEvent.click(within(skillTraceNode).getByRole('button', { name: '复跑整条运行记录' }));
    await waitFor(() => expect(runJobIds).toEqual(['scheduled_job_weekly_feedback']));
    expect(runJobBodies).toEqual([
      {
        return_immediately: true,
        source_run_id: 'scheduled_job_run_weekly_feedback',
        trigger_type: 'manual_rerun',
      },
    ]);
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
        resolved_agent_snapshot: {
          code: 'insight_agent',
          package_snapshot: {
            runtime_boundary: {
              script_execution: 'disabled_pending_sandbox',
              script_files: ['scripts/agent_run.py'],
            },
          },
        },
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
      snapshots: {
        agent: {
          code: 'insight_agent',
          package_snapshot: {
            runtime_boundary: {
              script_execution: 'disabled_pending_sandbox',
              script_files: ['scripts/agent_run.py'],
            },
          },
        },
      },
    });
    fireEvent.click(confirmRerunButton);
    await waitFor(() => expect(traceNodeRerunCalls).toEqual(['data_connection']));
    expect(await within(dialog).findByText('scheduled_job_run_weekly_feedback_data_connection_rerun')).toBeInTheDocument();
    expect(within(dialog).getByText('Trace DAG 数据连接节点单节点复跑完成')).toBeInTheDocument();
    expect(within(dialog).getAllByText('scheduled_job_run_weekly_feedback').length).toBeGreaterThan(0);
  });

  it('confirms an AI processing Trace DAG node rerun when preflight is ready', async () => {
    const { traceNodeRerunCalls } = installScheduledJobsFetchMock({
      runs: [buildReadyTraceNodeRerunRun()],
      traceNodeRerunMode: 'ready_all',
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看运行结果 scheduled_job_run_weekly_feedback' }));

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    const skillTraceNode = within(dialog).getByLabelText('Trace 节点 经过 Skill 处理后的内容');
    expect(skillTraceNode).toHaveTextContent('单节点复跑可用');
    expect(skillTraceNode).toHaveTextContent('副作用 model_gateway_call');

    fireEvent.click(within(skillTraceNode).getByRole('button', { name: '复跑预检' }));

    expect(await within(skillTraceNode).findByText('节点复跑预检')).toBeInTheDocument();
    expect(
      within(skillTraceNode).getByText('执行策略：单节点复跑控制项已满足，可以进入执行确认。'),
    ).toBeInTheDocument();
    expect(
      within(skillTraceNode).getByText('控制项：已满足 3 / 缺失 0 / 阻断 0 / 待确认 0'),
    ).toBeInTheDocument();
    expect(within(skillTraceNode).getByText('输入快照 · satisfied')).toBeInTheDocument();
    expect(within(skillTraceNode).getByText('模型幂等 · satisfied')).toBeInTheDocument();
    expect(within(skillTraceNode).getByText('下游动作失效策略 · satisfied')).toBeInTheDocument();
    expect(within(skillTraceNode).getByText('确认单节点复跑 · available')).toBeInTheDocument();

    fireEvent.click(within(skillTraceNode).getByRole('button', { name: '确认复跑' }));

    await waitFor(() => expect(traceNodeRerunCalls).toEqual(['skill_processing']));
    expect(await within(dialog).findByText('scheduled_job_run_weekly_feedback_skill_processing_rerun')).toBeInTheDocument();
    expect(within(dialog).getByText('Trace DAG AI 处理节点单节点复跑完成')).toBeInTheDocument();
  });

  it('confirms a result action Trace DAG node rerun when preflight is ready', async () => {
    const { traceNodeRerunCalls } = installScheduledJobsFetchMock({
      runs: [buildReadyTraceNodeRerunRun()],
      traceNodeRerunMode: 'ready_all',
    });

    render(<ScheduledJobsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '运行记录' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看运行结果 scheduled_job_run_weekly_feedback' }));

    const dialog = await screen.findByRole('dialog', { name: '运行结果详情' });
    const resultActionTraceNode = within(dialog).getByLabelText('Trace 节点 结果写入反馈内容');
    expect(resultActionTraceNode).toHaveTextContent('单节点复跑可用');
    expect(resultActionTraceNode).toHaveTextContent('副作用 idempotent_result_write');

    fireEvent.click(within(resultActionTraceNode).getByRole('button', { name: '复跑预检' }));

    expect(await within(resultActionTraceNode).findByText('节点复跑预检')).toBeInTheDocument();
    expect(
      within(resultActionTraceNode).getByText('执行策略：单节点复跑控制项已满足，可以进入执行确认。'),
    ).toBeInTheDocument();
    expect(
      within(resultActionTraceNode).getByText('控制项：已满足 3 / 缺失 0 / 阻断 0 / 待确认 0'),
    ).toBeInTheDocument();
    expect(within(resultActionTraceNode).getByText('动作输入快照 · satisfied')).toBeInTheDocument();
    expect(within(resultActionTraceNode).getByText('写入幂等 · satisfied')).toBeInTheDocument();
    expect(within(resultActionTraceNode).getByText('副作用防重 · satisfied')).toBeInTheDocument();
    expect(within(resultActionTraceNode).getByText('确认单节点复跑 · available')).toBeInTheDocument();

    fireEvent.click(within(resultActionTraceNode).getByRole('button', { name: '确认复跑' }));

    await waitFor(() => expect(traceNodeRerunCalls).toEqual(['result_action']));
    expect(await within(dialog).findByText('scheduled_job_run_weekly_feedback_result_action_rerun')).toBeInTheDocument();
    expect(within(dialog).getByText('Trace DAG 结果动作节点单节点复跑完成')).toBeInTheDocument();
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
            job_type: 'plugin_action_invoke',
            message: '插件执行调用完成',
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
    expect(within(dialog).getByText('运行摘要')).toBeInTheDocument();
    expect(within(dialog).getByText('插件执行调用完成')).toBeInTheDocument();
    expect(dialog).not.toHaveTextContent('No handler implemented');
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
                created_task_ids: [],
                feedback: {
                  task_ids: [],
                },
                label: 'Bug 确认后推进研发任务',
                records_imported: 0,
                status: 'deferred_to_bug_confirmation',
              },
            },
            finding_count: 1,
            report_id: 'code_inspection_report_ai',
            risk_level: 'critical',
            task_ids: [],
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
    expect(dialog).toHaveTextContent('Bug 确认后推进研发任务');
    expect(dialog).toHaveTextContent('deferred_to_bug_confirmation');
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
      {
        return_immediately: true,
        source_run_id: 'scheduled_job_run_weekly_feedback',
        trigger_type: 'manual_rerun',
      },
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
    expect(runJobBodies).toEqual([{ return_immediately: true, trigger_type: 'manual' }]);

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

  it('shows a returned queued run in the run table before the full reload finishes', async () => {
    const { runJobBodies } = installScheduledJobsFetchMock({
      deferRunListReload: true,
      jobs: [
        {
          enabled: true,
          execution_mode: 'ai_assisted',
          id: 'scheduled_job_weekly_feedback',
          job_type: 'code_repository_inspection',
          name: '代码仓库质量安全规范巡检',
          schedule_type: 'manual',
          status: 'active',
        },
      ],
      runResponse: Promise.resolve({
        id: 'scheduled_job_run_immediate',
        records_imported: 0,
        result_summary: {
          execution_nodes: {
            native_scan: { status: 'queued' },
          },
        },
        scheduled_job_id: 'scheduled_job_weekly_feedback',
        scheduled_job_name: '代码仓库质量安全规范巡检',
        status: 'queued',
        trigger_type: 'manual',
      }),
      runs: [],
    });

    render(<ScheduledJobsPage />);

    expect(await screen.findByText('代码仓库质量安全规范巡检')).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: '运行作业 代码仓库质量安全规范巡检' }));

    await waitFor(() =>
      expect(runJobBodies).toEqual([{ return_immediately: true, trigger_type: 'manual' }]),
    );
    expect(await screen.findByRole('tab', { name: '运行记录' })).toHaveAttribute('aria-selected', 'true');
    expect(
      await screen.findByRole('button', { name: '查看运行结果 scheduled_job_run_immediate' }),
    ).toBeInTheDocument();
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
