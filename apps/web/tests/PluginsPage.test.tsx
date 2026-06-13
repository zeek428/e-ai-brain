import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import PluginsPage from '../src/pages/Plugins';
import {
  ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
} from '../src/services/aiBrain';

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
}

async function findDialogByTitle(title: string) {
  let dialog: HTMLElement | undefined;
  await waitFor(() => {
    dialog = Array.from(document.body.querySelectorAll<HTMLElement>('[role="dialog"]')).find(
      (item) => within(item).queryByText(title),
    );
    expect(dialog).toBeTruthy();
  });
  return dialog!;
}

function getDialogField<T extends HTMLElement = HTMLElement>(dialog: HTMLElement, fieldId: string): T {
  const field = dialog.querySelector<T>(`#${fieldId}`);
  expect(field).toBeTruthy();
  return field!;
}

function pluginConnectionTestBody() {
  return {
    data: {
      checked_at: '2026-06-10T00:00:00Z',
      connection_id: 'connection_maxcompute_prod',
      diagnostics: [
        { detail: 'ai-brain-maxcompute-mcp.internal', name: 'endpoint_configured', status: 'succeeded' },
        { detail: 'tools/list 调用完成', latency_ms: 3, name: 'mcp_tools_list', status: 'succeeded' },
      ],
      environment: 'prod',
      latency_ms: 3,
      plugin_id: 'plugin_maxcompute',
      protocol: 'mcp_http',
      action_template_draft: {
        action_type: 'http_request',
        code: 'test_connection_maxcompute_prod',
        connection_id: 'connection_maxcompute_prod',
        description: '由连接测试请求回放生成，请确认请求路径、Params、Headers 和结果映射后保存。',
        name: '生产 MaxCompute 项目 请求执行',
        plugin_id: 'plugin_maxcompute',
        request_config: {
          headers: { Authorization: 'APPCODE 208b5b1456ee445ca47a42c' },
          method: 'POST',
          path: '/mcp',
          query: { start_pt: '{{current_date-7}}' },
        },
        result_mapping: { write_target: 'scheduled_job_result' },
        status: 'draft',
      },
      repair_suggestions: [],
      request_summary: {
        curl_command: "curl -X POST -H 'Authorization: APPCODE 208b5b1456ee445ca47a42c' 'https://ai-brain-maxcompute-mcp.internal/mcp?start_pt=20260604'",
        header_sources: { Authorization: 'auth_config.api_key_header' },
        headers: { Authorization: 'APPCODE 208b5b1456ee445ca47a42c' },
        masked_placeholder_headers: [],
        method: 'POST',
        original_request_config: {
          query: { start_pt: '{{current_date-7}}' },
        },
        protocol: 'mcp_http',
        query: { start_pt: '20260604' },
        url: 'https://ai-brain-maxcompute-mcp.internal/mcp?start_pt=20260604',
        variable_resolution_timezone: 'Asia/Shanghai',
        variable_resolutions: [
          {
            expression: '{{current_date-7}}',
            name: 'current_date',
            normalized_expression: '{{current_date-7}}',
            offset_days: -7,
            path: 'query.start_pt',
            resolved_text: '20260604',
            resolved_value: '20260604',
            status: 'resolved',
            token: '{{current_date-7}}',
          },
        ],
      },
      response_summary: { body_preview: '{"ok":true}', status_code: 200 },
      status: 'succeeded',
      test_history: [
        {
          action_template_draft: {
            action_type: 'http_request',
            code: 'test_connection_maxcompute_prod',
            connection_id: 'connection_maxcompute_prod',
            name: '生产 MaxCompute 项目 请求执行',
            plugin_id: 'plugin_maxcompute',
            request_config: {
              method: 'POST',
              path: '/mcp',
              query: { start_pt: '{{current_date-7}}' },
            },
            result_mapping: { write_target: 'scheduled_job_result' },
            status: 'draft',
          },
          checked_at: '2026-06-10T00:00:00Z',
          latency_ms: 3,
          repair_suggestions: [
            {
              code: 'inspect_request_replay',
              detail: '请检查历史请求参数和响应内容。',
              title: '对比请求回放',
            },
          ],
          request_summary: {
            method: 'POST',
            original_request_config: {
              query: { start_pt: '{{current_date-7}}' },
            },
            query: { start_pt: '20260604' },
            url: 'https://ai-brain-maxcompute-mcp.internal/mcp?start_pt=20260604',
          },
          response_summary: { body_preview: '{"ok":true}', status_code: 200 },
          status: 'succeeded',
        },
      ],
    },
  };
}

function installPluginsFetchMock(
  options: { deferConnectionTest?: boolean; emptyActionTemplates?: boolean; includeOfficialPlugins?: boolean } = {},
) {
  const actionBodies: unknown[] = [];
  const actionDeleteIds: string[] = [];
  const actionTrialBodies: unknown[] = [];
  const actionUpdateBodies: unknown[] = [];
  const connectionBodies: unknown[] = [];
  const connectionDeleteIds: string[] = [];
  const connectionListCalls: string[] = [];
  const connectionUpdateBodies: unknown[] = [];
  const connectionTestCalls: string[] = [];
  const pluginDeleteIds: string[] = [];
  const pluginUpdateBodies: unknown[] = [];
  const runnerBodies: unknown[] = [];
  const runnerDeleteIds: string[] = [];
  const runnerUpdateBodies: unknown[] = [];
  const connectionTestDeferred = options.deferConnectionTest
    ? createDeferred<Response>()
    : undefined;
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    if (input === '/api/system/plugins' && init?.method === 'GET') {
      const pluginItems = [
        {
          category: 'data_warehouse',
          code: 'aliyun_maxcompute',
          id: 'plugin_maxcompute',
          is_system: false,
          name: '阿里云 MaxCompute',
          protocol: 'mcp_http',
          risk_level: 'high',
          status: 'active',
        },
        ...(options.includeOfficialPlugins
          ? [
              {
                category: 'devops',
                code: 'gitlab',
                id: 'plugin_standard_gitlab',
                is_system: true,
                name: 'GitLab',
                protocol: 'http',
                risk_level: 'medium',
                status: 'active',
              },
              {
                category: 'devops',
                code: 'github',
                id: 'plugin_standard_github',
                is_system: true,
                name: 'GitHub',
                protocol: 'http',
                risk_level: 'medium',
                status: 'active',
              },
              {
                category: 'collaboration',
                code: 'email',
                id: 'plugin_standard_email',
                is_system: true,
                name: '邮箱',
                protocol: 'http',
                risk_level: 'medium',
                status: 'active',
              },
            ]
          : []),
      ];
      return jsonResponse({
        data: {
          items: pluginItems,
          total: pluginItems.length,
        },
      });
    }
    if (input === '/api/system/plugin-marketplace' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              action_count: 0,
              action_templates: ['GitLab 代码巡检', 'GitLab MR / 项目读取'],
              category: 'devops',
              code: 'gitlab',
              connection_defaults: {
                auth_config: {
                  header_name: 'PRIVATE-TOKEN',
                  secret_ref: 'vault/gitlab/token',
                },
                auth_type: 'api_key_header',
                endpoint_url: 'https://gitlab.com',
                environment: 'prod',
                max_retries: 1,
                name: '生产 GitLab 连接',
                request_config: {
                  query: {
                    api_version: 'v4',
                    group_id: '',
                    project_id: '',
                  },
                },
                status: 'active',
                timeout_seconds: 30,
              },
              connection_schema: {
                schema_version: 'v1',
                sections: [
                  {
                    fields: [
                      { key: 'project_id', label: 'GitLab 项目 ID', path: 'request_config.query.project_id', required: true, type: 'string' },
                      { key: 'api_version', label: 'API 版本', path: 'request_config.query.api_version', required: true, type: 'select' },
                    ],
                    key: 'project',
                    title: '项目配置',
                  },
                ],
              },
              connection_count: 0,
              connection_template_version: 'v1',
              id: 'marketplace_gitlab',
              installed: true,
              is_system: true,
              name: 'GitLab',
              plugin_id: 'plugin_standard_gitlab',
              protocol: 'http',
              publisher: 'AI Brain 官方',
              recommended_scenarios: ['代码仓库质量巡检', '漏洞发现同步'],
              risk_level: 'medium',
              status: 'active',
              summary: '连接 GitLab API，读取项目、MR 和代码质量数据。',
            },
            {
              action_count: 0,
              action_templates: ['GitHub 代码巡检', 'GitHub PR / 仓库读取'],
              category: 'devops',
              code: 'github',
              connection_defaults: {
                auth_config: { token_ref: 'vault/github/token' },
                auth_type: 'bearer',
                endpoint_url: 'https://api.github.com',
                environment: 'prod',
                max_retries: 1,
                name: '生产 GitHub 连接',
                request_config: {
                  headers: {
                    Accept: 'application/vnd.github+json',
                    'X-GitHub-Api-Version': '2022-11-28',
                  },
                  query: {
                    owner: '',
                    repo: '',
                  },
                },
                status: 'active',
                timeout_seconds: 30,
              },
              connection_schema: {
                schema_version: 'v1',
                sections: [
                  {
                    fields: [
                      { key: 'owner', label: '仓库 Owner', path: 'request_config.query.owner', required: true, type: 'string' },
                      { key: 'repo', label: '仓库名称', path: 'request_config.query.repo', required: true, type: 'string' },
                    ],
                    key: 'repository',
                    title: '仓库配置',
                  },
                ],
              },
              connection_count: 0,
              connection_template_version: 'v1',
              id: 'marketplace_github',
              installed: true,
              is_system: true,
              name: 'GitHub',
              plugin_id: 'plugin_standard_github',
              protocol: 'http',
              publisher: 'AI Brain 官方',
              recommended_scenarios: ['代码仓库质量巡检', '安全告警同步'],
              risk_level: 'medium',
              status: 'active',
              summary: '连接 GitHub API，读取仓库、PR 和代码扫描数据。',
            },
            {
              action_count: 0,
              action_templates: ['邮件通知发送'],
              category: 'collaboration',
              code: 'email',
              connection_defaults: {
                auth_config: {
                  header_name: 'Authorization',
                  secret_ref: 'vault/email/api_key',
                },
                auth_type: 'api_key_header',
                endpoint_url: 'https://mail-gateway.example.com/api',
                environment: 'prod',
                max_retries: 1,
                name: '生产邮箱通知连接',
                request_config: {
                  headers: { 'Content-Type': 'application/json' },
                  query: {
                    default_from: '',
                    default_to: '',
                    mail_provider: 'enterprise_mail_gateway',
                    subject_template: '[AI Brain] {{job_name}} 执行结果',
                  },
                },
                status: 'active',
                timeout_seconds: 30,
              },
              connection_schema: {
                schema_version: 'v1',
                sections: [
                  {
                    fields: [
                      { key: 'default_from', label: '默认发件人', path: 'request_config.query.default_from', required: true, type: 'string' },
                      { key: 'default_to', label: '默认收件人', path: 'request_config.query.default_to', required: false, supports_system_variables: true, type: 'string' },
                    ],
                    key: 'send',
                    title: '发件配置',
                  },
                ],
              },
              connection_count: options.includeOfficialPlugins ? 1 : 0,
              connection_template_version: 'v1',
              id: 'marketplace_email',
              installed: true,
              is_system: true,
              name: '邮箱',
              plugin_id: 'plugin_standard_email',
              protocol: 'http',
              publisher: 'AI Brain 官方',
              recommended_scenarios: ['代码巡检通知', '定时作业结果通知'],
              risk_level: 'medium',
              status: 'active',
              summary: '连接企业邮件网关或邮件 API。',
            },
          ],
          total: 3,
        },
      });
    }
    if (input === '/api/system/plugin-action-templates' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: options.emptyActionTemplates ? [] : [
            {
              action_type: 'mcp_tool',
              code: 'maxcompute_weekly_feedback',
              default_code: 'fetch_weekly_user_feedback',
              default_name: '获取本周用户反馈数据',
              form_defaults: {
                max_rows: 1000,
                returned_fields:
                  'feedback_id,user_id,product_id,module_code,feedback_type,content,sentiment,created_at',
                table_name: 'ods_user_feedback',
                time_field: 'created_at',
              },
              name: 'MaxCompute 每周用户反馈',
              plugin_code: 'aliyun_maxcompute',
              request_config: {
                fields: [
                  'feedback_id',
                  'user_id',
                  'product_id',
                  'module_code',
                  'feedback_type',
                  'content',
                  'sentiment',
                  'created_at',
                ],
                limit: 1000,
                sql_template:
                  "SELECT feedback_id, user_id, product_id, module_code, feedback_type, content, sentiment, created_at FROM ods_user_feedback WHERE created_at >= '${week_start}' AND created_at < '${week_end}' LIMIT 1000",
                table: 'ods_user_feedback',
                time_field: 'created_at',
                tool_name: 'maxcompute.execute_sql',
              },
              result_mapping: {
                insights_path: '$.insights',
                records_imported_path: '$.row_count',
                rows_path: '$.rows',
                write_target: 'user_feedback_insights',
              },
              template_version: 'v1',
            },
            {
              action_type: 'http_request',
              code: 'github_code_inspection',
              default_code: 'scan_github_code_inspection',
              default_name: 'GitHub 代码巡检',
              name: 'GitHub 代码巡检',
              plugin_code: 'github',
              request_config: {
                method: 'GET',
                path: '/repos/{{owner}}/{{repo}}/dependabot/alerts',
                query: { state: 'fixed', per_page: 50 },
              },
              result_mapping: {
                findings_path: '$.dependabot_alerts',
                write_target: 'code_inspection_reports',
              },
              template_version: 'v1',
            },
            {
              action_type: 'http_request',
              code: 'gitlab_code_inspection',
              default_code: 'scan_gitlab_code_inspection',
              default_name: 'GitLab 代码巡检',
              name: 'GitLab 代码巡检',
              plugin_code: 'gitlab',
              request_config: {
                method: 'GET',
                path: '/api/{{api_version}}/projects/{{project_id}}/vulnerability_findings',
                query: { state: 'detected', per_page: 100 },
              },
              result_mapping: {
                findings_path: '$.findings',
                write_target: 'code_inspection_reports',
              },
              template_version: 'v1',
            },
            {
              action_type: 'http_request',
              code: 'email_notification',
              default_code: 'send_email_notification',
              default_name: '发送邮件通知',
              name: '邮箱通知发送',
              plugin_code: 'email',
              request_config: {
                headers: { 'Content-Type': 'application/json' },
                method: 'POST',
                path: '/messages/send',
                query: {
                  body_template: '{{result_summary}}',
                  subject_template: '{{subject_template}}',
                  to: '{{default_to}}',
                },
              },
              result_mapping: {
                delivery_id_path: '$.message_id',
                delivery_status_path: '$.status',
                recipients_path: '$.recipients',
                subject_path: '$.subject',
                write_target: 'email_notifications',
              },
              template_version: 'v1',
            },
          ],
          total: options.emptyActionTemplates ? 0 : 4,
        },
      });
    }
    if (input === '/api/system/result-write-targets' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              code: 'scheduled_job_result',
              default_result_mapping: { write_target: 'scheduled_job_result' },
              form_label: '仅保存运行结果',
              label: '定时作业结果',
              mapping_fields: [
                {
                  key: 'records_imported_path',
                  label: '导入数量 JSONPath',
                  placeholder: '$.row_count',
                  required: false,
                },
              ],
            },
            {
              code: 'user_feedback_insights',
              default_result_mapping: {
                insights_path: '$.insights',
                records_imported_path: '$.row_count',
                rows_path: '$.rows',
                write_target: 'user_feedback_insights',
              },
              form_label: '用户洞察表',
              label: '用户洞察表',
              mapping_fields: [
                {
                  key: 'insights_path',
                  label: '洞察列表 JSONPath',
                  placeholder: '$.insights',
                  required: true,
                },
                {
                  key: 'records_imported_path',
                  label: '源表行数 JSONPath',
                  placeholder: '$.row_count',
                  required: false,
                },
                {
                  key: 'rows_path',
                  label: '原始行列表 JSONPath',
                  placeholder: '$.rows',
                  required: false,
                },
              ],
            },
            {
              code: 'code_inspection_reports',
              default_result_mapping: {
                branch_path: '$.branch',
                commit_sha_path: '$.commit_sha',
                findings_path: '$.findings',
                repository_id_path: '$.repository_id',
                risk_level_path: '$.risk_level',
                summary_path: '$.summary',
                write_target: 'code_inspection_reports',
              },
              form_label: '代码巡检报告',
              label: '代码巡检报告',
              mapping_fields: [
                {
                  key: 'findings_path',
                  label: 'Finding 列表 JSONPath',
                  placeholder: '$.findings',
                  required: true,
                },
                {
                  key: 'repository_id_path',
                  label: '仓库 ID JSONPath',
                  placeholder: '$.repository_id',
                  required: false,
                },
                {
                  key: 'risk_level_path',
                  label: '风险级别 JSONPath',
                  placeholder: '$.risk_level',
                  required: false,
                },
              ],
            },
            {
              code: 'email_notifications',
              default_result_mapping: {
                delivery_id_path: '$.message_id',
                delivery_status_path: '$.status',
                recipients_path: '$.recipients',
                subject_path: '$.subject',
                write_target: 'email_notifications',
              },
              form_label: '邮件通知记录',
              label: '邮件通知记录',
              mapping_fields: [
                {
                  key: 'recipients_path',
                  label: '收件人 JSONPath',
                  placeholder: '$.recipients',
                  required: true,
                },
                {
                  key: 'subject_path',
                  label: '主题 JSONPath',
                  placeholder: '$.subject',
                  required: false,
                },
                {
                  key: 'delivery_status_path',
                  label: '投递状态 JSONPath',
                  placeholder: '$.status',
                  required: false,
                },
                {
                  key: 'delivery_id_path',
                  label: '消息 ID JSONPath',
                  placeholder: '$.message_id',
                  required: false,
                },
              ],
            },
          ],
          total: 4,
        },
      });
    }
    if (input === '/api/system/ai-executor-runners' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              endpoint_url: 'runner://local',
              executor_types: ['codex', 'openclaw'],
              heartbeat_timeout_seconds: 120,
              heartbeat_age_seconds: 12,
              health_status: 'online',
              id: 'ai_executor_runner_001',
              last_heartbeat_at: '2026-06-13T09:00:00Z',
              max_concurrent_tasks: 1,
              metadata: { codex_path: '/Applications/Codex.app/Contents/Resources/codex' },
              name: 'Zeek Mac 本地执行器',
              protocol: 'runner_polling',
              setup_command: 'ai-brain-runner start --runner-id ai_executor_runner_001 --token <runner_token> --server http://127.0.0.1:8000',
              status: 'active',
              token_configured: true,
              workspace_roots: ['/Users/zeek/source/e-ai-brain'],
            },
          ],
          total: 1,
        },
      });
    }
    if (input === '/api/system/ai-executor-runners' && init?.method === 'POST') {
      runnerBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({
        data: {
          id: 'ai_executor_runner_created',
          name: '本地 OpenClaw 执行器',
          runner_token: 'runner-token-created',
          setup_command: 'ai-brain-runner start --runner-id ai_executor_runner_created --token runner-token-created --server http://127.0.0.1:8000',
          status: 'active',
          token_configured: true,
        },
      });
    }
    if (input === '/api/system/ai-executor-runners/ai_executor_runner_001' && init?.method === 'PATCH') {
      runnerUpdateBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'ai_executor_runner_001', status: 'active' } });
    }
    if (input === '/api/system/ai-executor-runners/ai_executor_runner_001' && init?.method === 'DELETE') {
      runnerDeleteIds.push('ai_executor_runner_001');
      return jsonResponse({ data: { deleted: true, id: 'ai_executor_runner_001' } });
    }
    if (input === '/api/system/plugins/plugin_maxcompute' && init?.method === 'PATCH') {
      pluginUpdateBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'plugin_maxcompute', status: 'active' } });
    }
    if (input === '/api/system/plugins/plugin_maxcompute' && init?.method === 'DELETE') {
      pluginDeleteIds.push('plugin_maxcompute');
      return jsonResponse({ data: { deleted: true, id: 'plugin_maxcompute' } });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/system/plugin-connections')
      && init?.method === 'GET'
    ) {
      connectionListCalls.push(input);
      const officialConnections = options.includeOfficialPlugins
        ? [
            {
              auth_type: 'api_key_header',
              endpoint_url: 'https://mail-gateway.example.com/api',
              environment: 'prod',
              id: 'connection_email_prod',
              name: '生产邮箱网关',
              plugin_id: 'plugin_standard_email',
              request_config: {
                headers: { 'Content-Type': 'application/json' },
                query: {
                  default_from: 'ai-brain@example.com',
                  default_to: 'owner@example.com',
                  mail_provider: 'enterprise_mail_gateway',
                  subject_template: '[AI Brain] {{job_name}} 执行结果',
                },
              },
              status: 'active',
            },
          ]
        : [];
      return jsonResponse({
        data: {
          items: [
            {
              auth_type: 'api_key_header',
              endpoint_url: 'https://ai-brain-maxcompute-mcp.internal/mcp',
              environment: 'prod',
              id: 'connection_maxcompute_prod',
              last_test_summary: {
                checked_at: '2026-06-10T00:00:00Z',
                error_code: 'HTTPError',
                error_message: 'HTTP Error 400: Bad Request',
                failed_step: 'network_request',
                latency_ms: 211,
                response_status_code: 400,
                status: 'failed',
              },
              name: '生产 MaxCompute 项目',
              plugin_id: 'plugin_maxcompute',
              request_config: {
                headers: { 'X-Workspace': 'prod' },
                query: { appCode: '208b5b1456ee445ca47a42c' },
              },
              status: 'active',
            },
            ...officialConnections,
          ],
          total: 1 + officialConnections.length,
        },
      });
    }
    if (input === '/api/system/plugin-connections/connection_maxcompute_prod' && init?.method === 'PATCH') {
      connectionUpdateBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'connection_maxcompute_prod', status: 'active' } });
    }
    if (input === '/api/system/plugin-connections/connection_maxcompute_prod' && init?.method === 'DELETE') {
      connectionDeleteIds.push('connection_maxcompute_prod');
      return jsonResponse({ data: { deleted: true, id: 'connection_maxcompute_prod' } });
    }
    if (input === '/api/system/plugin-connections' && init?.method === 'POST') {
      connectionBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'connection_created', status: 'active' } });
    }
    if (input === '/api/system/plugin-connections/connection_maxcompute_prod/test' && init?.method === 'POST') {
      connectionTestCalls.push(String(input));
      if (connectionTestDeferred) {
        return connectionTestDeferred.promise;
      }
      return jsonResponse(pluginConnectionTestBody());
    }
    if (input === '/api/system/plugin-actions' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              action_type: 'http_request',
              code: 'fetch_feedback_api',
              connection_id: 'connection_maxcompute_prod',
              id: 'action_feedback_api',
              name: '调用反馈 API',
              plugin_id: 'plugin_maxcompute',
              request_config: {
                headers: { Authorization: 'APPCODE old' },
                method: 'GET',
                path: '/zqf_api/feedback',
                query: { start_pt: '{{current_date-7}}' },
              },
              requires_human_review: false,
              result_mapping: { write_target: 'scheduled_job_result' },
              status: 'active',
            },
          ],
          total: 1,
        },
      });
    }
    if (input === '/api/system/scheduled-jobs' && init?.method === 'GET') {
      return jsonResponse({ data: { items: [], total: 0 } });
    }
    if (String(input).startsWith('/api/system/plugin-system-variables') && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              description: 'YYYYMMDD 格式，适合近 7 天起始分区',
              expression: '{{current_date-7}}',
              label: '当前日期 - 7 天',
              value: '20260603',
            },
          ],
          timezone: 'Asia/Shanghai',
        },
      });
    }
    if (input === '/api/system/plugin-invocation-logs' && init?.method === 'GET') {
      return jsonResponse({ data: { items: [], total: 0 } });
    }
    if (input === '/api/system/plugin-actions' && init?.method === 'POST') {
      actionBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'action_maxcompute_weekly', status: 'active' } });
    }
    if (input === '/api/system/plugin-actions/action_feedback_api' && init?.method === 'PATCH') {
      actionUpdateBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'action_feedback_api', status: 'active' } });
    }
    if (input === '/api/system/plugin-actions/action_feedback_api' && init?.method === 'DELETE') {
      actionDeleteIds.push('action_feedback_api');
      return jsonResponse({ data: { deleted: true, id: 'action_feedback_api' } });
    }
    if (input === '/api/system/plugin-actions/action_feedback_api/trial' && init?.method === 'POST') {
      actionTrialBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({
        data: {
          action_id: 'action_feedback_api',
          connection_id: 'connection_maxcompute_prod',
          latency_ms: 12,
          mapping_hits: [
            {
              key: 'records_imported_path',
              matched: true,
              path: '$.commits',
              value_preview: 8,
            },
          ],
          plugin_id: 'plugin_maxcompute',
          request_preview: {
            method: 'GET',
            query: { start_pt: '20260604' },
            url: 'https://ai-brain-maxcompute-mcp.internal/mcp?start_pt=20260604',
          },
          response_summary: { json: { commits: 8 } },
          status: 'succeeded',
          write_preview: {
            candidate_count: 0,
            preview_value: 8,
            records_imported: 8,
            sample_records: [],
            write_target: 'scheduled_job_result',
            write_target_label: '定时作业结果',
          },
        },
      });
    }
    throw new Error(`Unexpected fetch call: ${String(input)}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);
  return {
    actionBodies,
    actionDeleteIds,
    actionTrialBodies,
    actionUpdateBodies,
    connectionBodies,
    connectionDeleteIds,
    connectionListCalls,
    connectionTestCalls,
    connectionUpdateBodies,
    pluginDeleteIds,
    pluginUpdateBodies,
    resolveConnectionTest: () => {
      connectionTestDeferred?.resolve(jsonResponse(pluginConnectionTestBody()));
    },
    runnerBodies,
    runnerDeleteIds,
    runnerUpdateBodies,
  };
}

describe('PluginsPage', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('uses predefined plugin categories instead of a free text field', async () => {
    installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增插件' }));

    const dialog = await findDialogByTitle('新增插件');
    expect(within(dialog).queryByRole('textbox', { name: '分类' })).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('分类'));
    expect((await screen.findAllByText('数据仓库 / BI')).length).toBeGreaterThan(0);
    expect(screen.getByText('DevOps / 代码平台')).toBeInTheDocument();
    expect(screen.getByText('日志 / 监控')).toBeInTheDocument();
  });

  it('renders a compact system variable preview and opens the full table on demand', async () => {
    installPluginsFetchMock();

    render(<PluginsPage />);

    expect(await screen.findByText('系统变量预览')).toBeInTheDocument();
    expect(screen.getByText('常用变量')).toBeInTheDocument();
    expect(screen.getAllByText(/{{current_date-7}}/).length).toBeGreaterThan(0);
    expect(screen.queryByText('当前解析值')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '查看全部变量' }));

    const dialog = await findDialogByTitle('全部系统变量');
    expect(within(dialog).getAllByText('表达式').length).toBeGreaterThan(0);
    expect(within(dialog).getAllByText('当前解析值').length).toBeGreaterThan(0);
    expect(within(dialog).getByText('YYYYMMDD 格式，适合近 7 天起始分区')).toBeInTheDocument();
    expect(within(dialog).getByText('20260603')).toBeInTheDocument();
  });

  it('manages AI executor runners with OpenClaw support', async () => {
    const { runnerBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行器' }));

    expect(await screen.findByText('AI 执行器 Runner')).toBeInTheDocument();
    expect(screen.getByText('Zeek Mac 本地执行器')).toBeInTheDocument();
    expect(screen.getByText('online')).toBeInTheDocument();
    expect(screen.getByText('ai-brain-runner start --runner-id ai_executor_runner_001 --token <runner_token> --server http://127.0.0.1:8000')).toBeInTheDocument();
    expect(screen.getByText('openclaw')).toBeInTheDocument();
    expect(screen.getByText('/Users/zeek/source/e-ai-brain')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '新增执行器' }));

    const dialog = await findDialogByTitle('新增执行器');
    fireEvent.change(within(dialog).getByLabelText('名称'), {
      target: { value: '本地 OpenClaw 执行器' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(runnerBodies).toEqual([
        expect.objectContaining({
          executor_types: ['codex', 'openclaw'],
          name: '本地 OpenClaw 执行器',
          protocol: 'runner_polling',
          workspace_roots: ['/Users/zeek/source/e-ai-brain'],
        }),
      ]),
    );
    expect(await screen.findByText('runner-token-created')).toBeInTheDocument();
  });

  it('shows the official plugin marketplace and opens guided connection setup', async () => {
    installPluginsFetchMock({ includeOfficialPlugins: true });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '插件市场' }));

    expect(await screen.findByText('官方插件市场')).toBeInTheDocument();
    expect(screen.getByText('连接 GitHub API，读取仓库、PR 和代码扫描数据。')).toBeInTheDocument();
    expect(screen.getByText('安全告警同步')).toBeInTheDocument();
    expect(screen.getByText('GitHub 代码巡检')).toBeInTheDocument();
    expect(screen.getByText('仓库 Owner')).toBeInTheDocument();
    expect(screen.getByText('仓库名称')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '配置市场插件 GitHub' }));

    const dialog = await findDialogByTitle('新增连接');
    expect(within(dialog).getByLabelText('名称')).toHaveValue('生产 GitHub 连接');
    expect(within(dialog).getByDisplayValue('https://api.github.com')).toBeInTheDocument();
    expect(within(dialog).getByText('GitHub (http)')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('owner')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('repo')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('application/vnd.github+json')).toBeInTheDocument();
  });

  it('opens official action templates from the plugin marketplace', async () => {
    const { actionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '插件市场' }));
    fireEvent.click(await screen.findByRole('button', { name: '从市场插件 GitHub 创建执行' }));

    const dialog = await findDialogByTitle('新增执行');
    expect(within(dialog).getByText('GitHub (http)')).toBeInTheDocument();
    expect(within(dialog).getByText('代码巡检报告')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('请求路径')).toHaveValue('/repos/{{owner}}/{{repo}}/dependabot/alerts');
    expect(within(dialog).getByDisplayValue('state')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('fixed')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          action_type: 'http_request',
          code: 'scan_github_code_inspection',
          name: 'GitHub 代码巡检',
          plugin_id: 'plugin_standard_github',
          request_config: expect.objectContaining({
            method: 'GET',
            path: '/repos/{{owner}}/{{repo}}/dependabot/alerts',
            query: expect.objectContaining({ state: 'fixed', per_page: 50 }),
          }),
          result_mapping: expect.objectContaining({
            findings_path: '$.dependabot_alerts',
            write_target: 'code_inspection_reports',
          }),
        }),
      ]),
    );
  });

  it('does not create marketplace actions when the server template catalog is missing', async () => {
    const { actionBodies } = installPluginsFetchMock({
      emptyActionTemplates: true,
      includeOfficialPlugins: true,
    });
    const warningSpy = vi.spyOn(message, 'warning');

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '插件市场' }));
    fireEvent.click(await screen.findByRole('button', { name: '从市场插件 GitHub 创建执行' }));

    expect(warningSpy).toHaveBeenCalledWith('执行模板目录未返回该官方插件模板，请刷新服务端模板目录后重试');
    expect(screen.queryByText('新增执行')).not.toBeInTheDocument();
    expect(actionBodies).toEqual([]);
  });

  it('applies assistant plugin action drafts to the action form', async () => {
    const { actionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });
    window.sessionStorage.setItem(
      ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
      JSON.stringify({
        draftId: 'assistant_draft_github_plugin_action',
        payload: {
          action_type: 'http_request',
          code: 'scan_github_code_inspection',
          name: 'GitHub 代码巡检',
          plugin_id: 'plugin_standard_github',
          request_config: {
            method: 'GET',
            path: '/repos/{{owner}}/{{repo}}/code-scanning/alerts',
            query: { per_page: 100, state: 'open' },
          },
          result_mapping: {
            findings_path: '$.findings',
            write_target: 'code_inspection_reports',
          },
          status: 'active',
        },
        title: 'GitHub 代码巡检执行',
      }),
    );

    render(<PluginsPage />);

    const dialog = await findDialogByTitle('新增执行');
    expect(window.sessionStorage.getItem(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY)).toBeNull();
    expect(within(dialog).getByText('GitHub (http)')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('名称')).toHaveValue('GitHub 代码巡检');
    expect(within(dialog).getByLabelText('编码')).toHaveValue('scan_github_code_inspection');
    expect(within(dialog).getByLabelText('请求路径')).toHaveValue('/repos/{{owner}}/{{repo}}/code-scanning/alerts');
    expect(within(dialog).getByText('代码巡检报告')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('per_page')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('100')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('state')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('open')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          action_type: 'http_request',
          code: 'scan_github_code_inspection',
          name: 'GitHub 代码巡检',
          plugin_id: 'plugin_standard_github',
          request_config: expect.objectContaining({
            method: 'GET',
            path: '/repos/{{owner}}/{{repo}}/code-scanning/alerts',
            query: expect.objectContaining({ per_page: 100, state: 'open' }),
          }),
          result_mapping: expect.objectContaining({
            findings_path: '$.findings',
            write_target: 'code_inspection_reports',
          }),
        }),
      ]),
    );
  });

  it('applies assistant plugin connection drafts to the connection form', async () => {
    const { connectionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });
    window.sessionStorage.setItem(
      ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
      JSON.stringify({
        draftId: 'assistant_draft_github_plugin_connection',
        payload: {
          auth_config: { token_ref: 'vault/github/token' },
          auth_type: 'bearer',
          endpoint_url: 'https://api.github.com',
          environment: 'prod',
          max_retries: 1,
          name: '生产 GitHub 连接',
          plugin_id: 'plugin_standard_github',
          request_config: {
            headers: {
              Accept: 'application/vnd.github+json',
              'X-GitHub-Api-Version': '2022-11-28',
            },
            query: { owner: '', repo: '' },
          },
          status: 'active',
          timeout_seconds: 30,
        },
        title: 'GitHub API 连接',
      }),
    );

    render(<PluginsPage />);

    const dialog = await findDialogByTitle('新增连接');
    expect(window.sessionStorage.getItem(ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY)).toBeNull();
    expect(within(dialog).getByText('GitHub (http)')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('名称')).toHaveValue('生产 GitHub 连接');
    expect(within(dialog).getByLabelText('Endpoint URL')).toHaveValue('https://api.github.com');
    await waitFor(() => expect(within(dialog).getByDisplayValue('vault/github/token')).toBeInTheDocument());
    expect(within(dialog).getByDisplayValue('Accept')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('application/vnd.github+json')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('X-GitHub-Api-Version')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('owner')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('repo')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(connectionBodies).toEqual([
        expect.objectContaining({
          auth_config: { token_ref: 'vault/github/token' },
          auth_type: 'bearer',
          endpoint_url: 'https://api.github.com',
          environment: 'prod',
          max_retries: 1,
          name: '生产 GitHub 连接',
          plugin_id: 'plugin_standard_github',
          request_config: {
            headers: {
              Accept: 'application/vnd.github+json',
              'X-GitHub-Api-Version': '2022-11-28',
            },
            query: { owner: '', repo: '' },
          },
          status: 'active',
          timeout_seconds: 30,
        }),
      ]),
    );
  });

  it('remembers assistant connection drafts and resolves dependent action drafts', async () => {
    const { actionBodies, connectionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });
    window.sessionStorage.setItem(
      ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
      JSON.stringify({
        draftId: 'assistant_draft_github_plugin_connection',
        payload: {
          auth_config: { token_ref: 'vault/github/token' },
          auth_type: 'bearer',
          endpoint_url: 'https://api.github.com',
          environment: 'prod',
          name: '生产 GitHub 连接',
          plugin_id: 'plugin_standard_github',
          request_config: { headers: { Accept: 'application/vnd.github+json' } },
          status: 'active',
          timeout_seconds: 30,
        },
        title: 'GitHub API 连接',
      }),
    );

    render(<PluginsPage />);

    const connectionDialog = await findDialogByTitle('新增连接');
    fireEvent.click(within(connectionDialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() => expect(connectionBodies).toHaveLength(1));
    expect(JSON.parse(window.sessionStorage.getItem('ai_brain_assistant_draft_resolution') ?? '{}')).toEqual({
      assistant_draft_github_plugin_connection: {
        resource_id: 'connection_created',
        resource_type: 'plugin_connection',
        title: 'GitHub API 连接',
      },
    });

    cleanup();
    window.sessionStorage.setItem(
      ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
      JSON.stringify({
        draftId: 'assistant_draft_github_plugin_action',
        payload: {
          action_type: 'http_request',
          assistant_prerequisite_draft_ids: ['assistant_draft_github_plugin_connection'],
          code: 'scan_github_code_inspection',
          name: 'GitHub 代码巡检',
          plugin_id: 'plugin_standard_github',
          request_config: {
            method: 'GET',
            path: '/repos/{{owner}}/{{repo}}/code-scanning/alerts',
            query: { state: 'open' },
          },
          result_mapping: {
            findings_path: '$.findings',
            write_target: 'code_inspection_reports',
          },
          status: 'active',
        },
        title: 'GitHub 代码巡检执行',
      }),
    );

    render(<PluginsPage />);

    const actionDialog = await findDialogByTitle('新增执行');
    fireEvent.click(within(actionDialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          code: 'scan_github_code_inspection',
          connection_id: 'connection_created',
          plugin_id: 'plugin_standard_github',
        }),
      ]),
    );
  });

  it('warns when deleting resources in use and can delete unused actions', async () => {
    const { actionDeleteIds, pluginDeleteIds } = installPluginsFetchMock();

    render(<PluginsPage />);

    expect(await screen.findByText('阿里云 MaxCompute')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '删除插件 阿里云 MaxCompute' }));
    expect(await screen.findByText('当前对象正在被使用，不能删除。请先解除下面的引用，或将其停用。')).toBeInTheDocument();
    expect(screen.getByText('连接：')).toBeInTheDocument();
    expect(screen.getByText('生产 MaxCompute 项目')).toBeInTheDocument();
    expect(screen.getByText('执行：')).toBeInTheDocument();
    expect(screen.getByText('调用反馈 API')).toBeInTheDocument();
    expect(pluginDeleteIds).toEqual([]);
    fireEvent.click(screen.getByRole('button', { name: /知道了|OK|确\s*定/ }));

    fireEvent.click(await screen.findByRole('tab', { name: '执行' }));
    fireEvent.click(await screen.findByRole('button', { name: '删除执行 调用反馈 API' }));
    await screen.findByText('确定删除执行「调用反馈 API」吗？');
    fireEvent.click(screen.getAllByRole('button', { name: /删\s*除/ }).at(-1)!);
    await waitFor(() => expect(actionDeleteIds).toEqual(['action_feedback_api']));
  });

  it('uses predefined connection environments and can test a connection', async () => {
    const { connectionBodies, connectionTestCalls } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));
    expect(await screen.findByText('生产')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /测试/ }));
    await waitFor(() =>
      expect(connectionTestCalls).toEqual(['/api/system/plugin-connections/connection_maxcompute_prod/test']),
    );
    expect(await screen.findByText('请求调试台')).toBeInTheDocument();
    expect(screen.getByText('请求回放台')).toBeInTheDocument();
    expect(screen.getByText('最近测试记录')).toBeInTheDocument();
    expect(screen.getByText('变量解析前 / 后差异')).toBeInTheDocument();
    expect(screen.getAllByText('解析前').length).toBeGreaterThan(0);
    expect(screen.getAllByText('解析后').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: '复制为执行模板' })).toBeInTheDocument();
    expect(screen.getByText('最终请求 URL')).toBeInTheDocument();
    expect(screen.getByText('可复制 cURL')).toBeInTheDocument();
    expect(screen.getByText('动态变量解析')).toBeInTheDocument();
    expect(screen.getAllByText('Timezone: Asia/Shanghai').length).toBeGreaterThan(0);
    expect(screen.getAllByText('query.start_pt').length).toBeGreaterThan(0);
    expect(screen.getAllByText('{{current_date-7}}').length).toBeGreaterThan(0);
    expect(screen.getByText('-7')).toBeInTheDocument();
    expect(screen.getByText('Header 来源')).toBeInTheDocument();
    expect(screen.getByText('Authorization')).toBeInTheDocument();
    expect(screen.getByText('auth_config.api_key_header')).toBeInTheDocument();
    expect(screen.getByText('远端响应信息')).toBeInTheDocument();
    expect(screen.getByText('原始请求配置')).toBeInTheDocument();
    expect(screen.getByText('完整请求 JSON')).toBeInTheDocument();
    expect(screen.getAllByText(/curl -X POST -H 'Authorization: APPCODE 208b5b1456ee445ca47a42c'/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/ai-brain-maxcompute-mcp\.internal\/mcp\?start_pt=20260604/).length).toBeGreaterThan(0);
    let testDialog: HTMLElement | undefined;
    await waitFor(() => {
      testDialog = Array.from(document.body.querySelectorAll<HTMLElement>('[role="dialog"]')).find(
        (item) => within(item).queryAllByText('连接测试诊断').length > 0,
      );
      expect(testDialog).toBeTruthy();
    });
    const resolvedTestDialog = testDialog!;
    const historyExpandIcon = resolvedTestDialog.querySelector<HTMLElement>('.ant-table-row-expand-icon');
    expect(historyExpandIcon).toBeTruthy();
    fireEvent.click(historyExpandIcon!);
    expect(within(resolvedTestDialog).getByText('历史请求详情')).toBeInTheDocument();
    expect(within(resolvedTestDialog).getByText('历史修复建议')).toBeInTheDocument();
    expect(within(resolvedTestDialog).getByText('对比请求回放')).toBeInTheDocument();
    expect(within(resolvedTestDialog).getByText('历史完整请求 JSON')).toBeInTheDocument();
    expect(within(resolvedTestDialog).getByText('历史远端响应信息')).toBeInTheDocument();
    expect(within(resolvedTestDialog).getByText('历史执行模板草案')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '复制为执行模板' }));
    const actionDialogFromReplay = await findDialogByTitle('新增执行');
    expect(within(actionDialogFromReplay).getByLabelText('名称')).toHaveValue('生产 MaxCompute 项目 请求执行');
    expect(within(actionDialogFromReplay).getByLabelText('编码')).toHaveValue('test_connection_maxcompute_prod');
    expect(within(actionDialogFromReplay).getByText('阿里云 MaxCompute (mcp_http)')).toBeInTheDocument();
    expect(within(actionDialogFromReplay).getByText('生产 MaxCompute 项目 (prod)')).toBeInTheDocument();
    fireEvent.click(within(actionDialogFromReplay).getByRole('button', { name: /取\s*消/ }));

    fireEvent.click(screen.getByRole('button', { name: '新增连接' }));
    const dialog = await findDialogByTitle('新增连接');
    expect(within(dialog).queryByRole('textbox', { name: '环境' })).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('认证配置 JSON')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('请求配置 JSON')).not.toBeInTheDocument();
    fireEvent.mouseDown(within(dialog).getByLabelText('环境'));
    expect(await screen.findByText('预发 / Staging')).toBeInTheDocument();
    expect(screen.getAllByText('生产').length).toBeGreaterThan(0);

    fireEvent.change(getDialogField<HTMLInputElement>(dialog, 'name'), { target: { value: '生产 MaxCompute API' } });
    fireEvent.change(getDialogField<HTMLInputElement>(dialog, 'endpoint_url'), {
      target: { value: 'https://example.aliyunapi.com' },
    });
    fireEvent.mouseDown(getDialogField<HTMLInputElement>(dialog, 'auth_type'));
    fireEvent.click((await screen.findAllByText('api_key_header')).at(-1)!);
    await waitFor(() => expect(getDialogField<HTMLInputElement>(dialog, 'header_name')).toBeInTheDocument());
    const headerNameInput = getDialogField<HTMLInputElement>(dialog, 'header_name');
    fireEvent.change(headerNameInput, { target: { value: 'Authorization' } });
    fireEvent.change(getDialogField<HTMLInputElement>(dialog, 'secret_ref'), {
      target: { value: 'vault/maxcompute/appcode' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /添加 Params/ }));
    fireEvent.change(within(dialog).getByPlaceholderText('参数名'), { target: { value: 'start_pt' } });
    fireEvent.change(within(dialog).getByPlaceholderText('参数值'), { target: { value: '{{current_date-7}}' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /添加 Headers/ }));
    fireEvent.change(within(dialog).getByPlaceholderText('Header 名'), { target: { value: 'Authorization' } });
    fireEvent.change(within(dialog).getByPlaceholderText('Header 值'), {
      target: { value: 'APPCODE 208b5b1456ee445ca47a42c' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(connectionBodies).toEqual([
        expect.objectContaining({
          auth_config: {
            header_name: 'Authorization',
            secret_ref: 'vault/maxcompute/appcode',
          },
          auth_type: 'api_key_header',
          endpoint_url: 'https://example.aliyunapi.com',
          name: '生产 MaxCompute API',
          request_config: {
            headers: { Authorization: 'APPCODE 208b5b1456ee445ca47a42c' },
            query: { start_pt: '{{current_date-7}}' },
          },
        }),
      ]),
    );
  }, 10000);

  it('filters plugin connections by environment', async () => {
    const { connectionListCalls } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));
    fireEvent.mouseDown(await screen.findByText('全部环境'));
    const prodOptions = await screen.findAllByText('生产');
    fireEvent.click(prodOptions.at(-1)!);

    await waitFor(() =>
      expect(connectionListCalls).toContain('/api/system/plugin-connections?environment=prod'),
    );
  });

  it('shows latest connection test summary in the connection list', async () => {
    installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));

    expect(await screen.findByText('最近测试')).toBeInTheDocument();
    expect(await screen.findByText('failed')).toBeInTheDocument();
    expect(screen.getByText('HTTPError')).toBeInTheDocument();
    expect(screen.getByText('211ms')).toBeInTheDocument();
  });

  it('shows an in-progress state while a connection test is running', async () => {
    const { connectionTestCalls, resolveConnectionTest } = installPluginsFetchMock({
      deferConnectionTest: true,
    });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));
    fireEvent.click(await screen.findByRole('button', { name: '测试连接 生产 MaxCompute 项目' }));

    await waitFor(() =>
      expect(connectionTestCalls).toEqual(['/api/system/plugin-connections/connection_maxcompute_prod/test']),
    );
    const testingButton = await screen.findByRole('button', {
      name: '连接测试中 生产 MaxCompute 项目',
    });
    expect(testingButton).toBeDisabled();
    expect(testingButton).toHaveTextContent('测试中');
    expect(screen.getByText('正在测试连接「生产 MaxCompute 项目」，请稍候...')).toBeInTheDocument();

    resolveConnectionTest();

    expect(await screen.findByText('请求调试台')).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole('button', { name: '测试连接 生产 MaxCompute 项目' })).toBeInTheDocument(),
    );
  });

  it('can edit existing plugins', async () => {
    const { pluginUpdateBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '编辑插件 阿里云 MaxCompute' }));
    const dialog = await findDialogByTitle('编辑插件');
    fireEvent.change(within(dialog).getByLabelText('名称'), {
      target: { value: '阿里云 MaxCompute 网关' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));
    await waitFor(() =>
      expect(pluginUpdateBodies).toEqual([
        expect.objectContaining({
          name: '阿里云 MaxCompute 网关',
          protocol: 'mcp_http',
        }),
      ]),
    );
  });

  it('locks official plugins while providing GitLab GitHub and email connection defaults', async () => {
    const { connectionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });

    render(<PluginsPage />);

    expect(await screen.findByText('GitLab')).toBeInTheDocument();
    expect(screen.getByText('GitHub')).toBeInTheDocument();
    expect(screen.getByText('邮箱')).toBeInTheDocument();
    expect(screen.getAllByText('官方标准').length).toBeGreaterThanOrEqual(3);
    expect(screen.queryByRole('button', { name: '编辑插件 GitLab' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '删除插件 GitLab' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '编辑插件 GitHub' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '删除插件 GitHub' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '编辑插件 邮箱' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '删除插件 邮箱' })).not.toBeInTheDocument();

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));
    fireEvent.click(screen.getByRole('button', { name: '新增连接' }));
    let dialog = await findDialogByTitle('新增连接');
    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('GitLab (http)'));

    expect(within(dialog).getByLabelText('Endpoint URL')).toHaveValue('https://gitlab.com');
    expect(await within(dialog).findByLabelText('Header 名')).toHaveValue('PRIVATE-TOKEN');
    expect(within(dialog).getByDisplayValue('api_version')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('v4')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('group_id')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('project_id')).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '生产 GitLab' } });
    fireEvent.change(within(dialog).getByLabelText('Header 值/密钥引用'), {
      target: { value: 'vault/gitlab/prod-token' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(connectionBodies.at(-1)).toEqual(
        expect.objectContaining({
          auth_config: {
            header_name: 'PRIVATE-TOKEN',
            secret_ref: 'vault/gitlab/prod-token',
          },
          auth_type: 'api_key_header',
          endpoint_url: 'https://gitlab.com',
          name: '生产 GitLab',
          plugin_id: 'plugin_standard_gitlab',
          request_config: {
            query: {
              api_version: 'v4',
              group_id: '',
              project_id: '',
            },
          },
        }),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增连接' }));
    dialog = await findDialogByTitle('新增连接');
    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('GitHub (http)'));

    expect(within(dialog).getByLabelText('Endpoint URL')).toHaveValue('https://api.github.com');
    expect(await within(dialog).findByLabelText('Token 引用')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('Accept')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('application/vnd.github+json')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('X-GitHub-Api-Version')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('2022-11-28')).toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('邮箱 (http)'));

    expect(within(dialog).getByLabelText('Endpoint URL')).toHaveValue('https://mail-gateway.example.com/api');
    expect(await within(dialog).findByLabelText('Header 名')).toHaveValue('Authorization');
    expect(within(dialog).getByDisplayValue('Content-Type')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('application/json')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('mail_provider')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('enterprise_mail_gateway')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('default_from')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('default_to')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('subject_template')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('[AI Brain] {{job_name}} 执行结果')).toBeInTheDocument();
  });

  it('can edit existing connections', async () => {
    const { connectionUpdateBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    const connectionsTab = screen.getByRole('tab', { name: '连接' });
    fireEvent.click(connectionsTab);
    await waitFor(() => expect(connectionsTab).toHaveAttribute('aria-selected', 'true'));
    fireEvent.click(await screen.findByRole('button', { name: '编辑连接 生产 MaxCompute 项目' }));
    const dialog = await findDialogByTitle('编辑连接');
    fireEvent.change(within(dialog).getByLabelText('名称'), {
      target: { value: '生产 MaxCompute 项目 v2' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /添加 Params/ }));
    fireEvent.change(within(dialog).getAllByPlaceholderText('参数名').at(-1)!, {
      target: { value: 'end_pt' },
    });
    fireEvent.change(within(dialog).getAllByPlaceholderText('参数值').at(-1)!, {
      target: { value: '{{current_date}}' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));
    await waitFor(() =>
      expect(connectionUpdateBodies).toEqual([
        expect.objectContaining({
          name: '生产 MaxCompute 项目 v2',
          request_config: {
            headers: { 'X-Workspace': 'prod' },
            query: {
              appCode: '208b5b1456ee445ca47a42c',
              end_pt: '{{current_date}}',
            },
          },
        }),
      ]),
    );
  });

  it('can edit existing actions', async () => {
    const { actionUpdateBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    const actionsTab = screen.getByRole('tab', { name: '执行' });
    fireEvent.click(actionsTab);
    await waitFor(() => expect(actionsTab).toHaveAttribute('aria-selected', 'true'));
    fireEvent.click(await screen.findByRole('button', { name: '编辑执行 调用反馈 API' }));
    const dialog = await findDialogByTitle('编辑执行');
    fireEvent.change(within(dialog).getByLabelText('请求路径'), {
      target: { value: '/zqf_api/feedback/v2' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));
    await waitFor(() =>
      expect(actionUpdateBodies).toEqual([
        expect.objectContaining({
          code: 'fetch_feedback_api',
          request_config: {
            headers: { Authorization: 'APPCODE old' },
            method: 'GET',
            path: '/zqf_api/feedback/v2',
            query: { start_pt: '{{current_date-7}}' },
          },
        }),
      ]),
    );
  });

  it('builds request config from visual params and headers by default', async () => {
    const { actionBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行' }));
    fireEvent.click(screen.getByRole('button', { name: '新增执行' }));

    const dialog = await findDialogByTitle('新增执行');
    expect(within(dialog).getByLabelText('结果写入目标')).toBeInTheDocument();
    expect(within(dialog).getByText('仅保存运行结果')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('导入数量 JSONPath')).toBeInTheDocument();
    expect(within(dialog).queryByLabelText('洞察列表 JSONPath')).not.toBeInTheDocument();
    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click((await screen.findAllByText('阿里云 MaxCompute (mcp_http)')).at(-1)!);
    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '调用反馈 API' } });
    fireEvent.change(within(dialog).getByLabelText('编码'), { target: { value: 'fetch_feedback_api' } });
    fireEvent.change(within(dialog).getByLabelText('请求路径'), { target: { value: '/zqf_api/feedback' } });

    fireEvent.click(within(dialog).getByRole('button', { name: /添加 Params/ }));
    fireEvent.change(within(dialog).getByPlaceholderText('参数名'), { target: { value: 'start_pt' } });
    fireEvent.mouseDown(within(dialog).getByText('系统变量'));
    fireEvent.click((await screen.findAllByText('当前日期 - 7 天')).at(-1)!);

    fireEvent.click(within(dialog).getByRole('button', { name: /添加 Headers/ }));
    fireEvent.change(within(dialog).getByPlaceholderText('Header 名'), { target: { value: 'Authorization' } });
    fireEvent.change(within(dialog).getByPlaceholderText('Header 值'), {
      target: { value: 'APPCODE 208b5b1456ee445ca47a42c' },
    });

    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          code: 'fetch_feedback_api',
          name: '调用反馈 API',
          request_config: {
            headers: { Authorization: 'APPCODE 208b5b1456ee445ca47a42c' },
            method: 'GET',
            path: '/zqf_api/feedback',
            query: { start_pt: '{{current_date-7}}' },
          },
          result_mapping: { write_target: 'scheduled_job_result' },
        }),
      ]),
    );
  });

  it('updates result mapping fields when the write target changes', async () => {
    installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行' }));
    fireEvent.click(screen.getByRole('button', { name: '新增执行' }));

    const dialog = await findDialogByTitle('新增执行');
    expect(within(dialog).getByLabelText('导入数量 JSONPath')).toBeInTheDocument();
    expect(within(dialog).queryByLabelText('洞察列表 JSONPath')).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('结果写入目标'));
    fireEvent.click(await screen.findByText('用户洞察表'));

    expect(within(dialog).getByLabelText('洞察列表 JSONPath')).toHaveValue('$.insights');
    expect(within(dialog).getByLabelText('源表行数 JSONPath')).toHaveValue('$.row_count');
    expect(within(dialog).getByLabelText('原始行列表 JSONPath')).toHaveValue('$.rows');
    expect(within(dialog).queryByLabelText('导入数量 JSONPath')).not.toBeInTheDocument();
  });

  it('offers code inspection reports as an action write target', async () => {
    const { actionBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行' }));
    fireEvent.click(screen.getByRole('button', { name: '新增执行' }));

    const dialog = await findDialogByTitle('新增执行');
    fireEvent.mouseDown(within(dialog).getByLabelText('结果写入目标'));
    fireEvent.click(await screen.findByText('代码巡检报告'));

    expect(within(dialog).getByLabelText('Finding 列表 JSONPath')).toHaveValue('$.findings');
    expect(within(dialog).getByLabelText('仓库 ID JSONPath')).toHaveValue('$.repository_id');
    expect(within(dialog).getByLabelText('风险级别 JSONPath')).toHaveValue('$.risk_level');
    expect(within(dialog).queryByLabelText('洞察列表 JSONPath')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('导入数量 JSONPath')).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click((await screen.findAllByText('阿里云 MaxCompute (mcp_http)')).at(-1)!);
    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '扫描仓库质量' } });
    fireEvent.change(within(dialog).getByLabelText('编码'), { target: { value: 'scan_repository_quality' } });
    fireEvent.change(within(dialog).getByLabelText('请求路径'), { target: { value: '/quality/scan' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          code: 'scan_repository_quality',
          result_mapping: {
            branch_path: '$.branch',
            commit_sha_path: '$.commit_sha',
            findings_path: '$.findings',
            repository_id_path: '$.repository_id',
            risk_level_path: '$.risk_level',
            summary_path: '$.summary',
            write_target: 'code_inspection_reports',
          },
        }),
      ]),
    );
  });

  it('creates a MaxCompute weekly feedback action from guided fields while allowing advanced JSON edits', async () => {
    const { actionBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行' }));
    fireEvent.click(screen.getByRole('button', { name: '新增执行' }));

    const dialog = await findDialogByTitle('新增执行');
    fireEvent.mouseDown(within(dialog).getByLabelText('配置场景'));
    fireEvent.click(await screen.findByText('MaxCompute 每周用户反馈'));

    expect(within(dialog).getByText('用户洞察表')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('洞察列表 JSONPath')).toHaveValue('$.insights');
    fireEvent.change(within(dialog).getByLabelText('洞察列表 JSONPath'), {
      target: { value: '$.analysis.insights' },
    });
    expect(within(dialog).getByLabelText('表名')).toHaveValue('ods_user_feedback');
    expect(within(dialog).getByLabelText('时间字段')).toHaveValue('created_at');
    expect(within(dialog).getByLabelText('返回字段')).toHaveValue(
      'feedback_id,user_id,product_id,module_code,feedback_type,content,sentiment,created_at',
    );

    fireEvent.change(within(dialog).getByLabelText('最大行数'), { target: { value: '500' } });
    fireEvent.click(within(dialog).getByText('高级 JSON 修改'));
    fireEvent.change(within(dialog).getByLabelText('请求配置 JSON'), {
      target: {
        value:
          '{"tool_name":"maxcompute.execute_sql","table":"ods_user_feedback","time_field":"created_at","limit":500,"sql_template":"SELECT feedback_id, content FROM ods_user_feedback LIMIT 500"}',
      },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          action_type: 'mcp_tool',
          code: 'fetch_weekly_user_feedback',
          name: '获取本周用户反馈数据',
          request_config: expect.objectContaining({
            limit: 500,
            table: 'ods_user_feedback',
            tool_name: 'maxcompute.execute_sql',
          }),
          result_mapping: {
            insights_path: '$.analysis.insights',
            records_imported_path: '$.row_count',
            rows_path: '$.rows',
            write_target: 'user_feedback_insights',
          },
        }),
      ]),
    );
  });

  it('creates official GitHub and GitLab code inspection actions from scene templates', async () => {
    const { actionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行' }));
    fireEvent.click(screen.getByRole('button', { name: '新增执行' }));

    const dialog = await findDialogByTitle('新增执行');
    fireEvent.mouseDown(within(dialog).getByLabelText('配置场景'));
    fireEvent.click(await screen.findByText('GitHub 代码巡检'));

    expect(within(dialog).getByText('代码巡检报告')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('请求路径')).toHaveValue('/repos/{{owner}}/{{repo}}/dependabot/alerts');
    expect(within(dialog).getByLabelText('Finding 列表 JSONPath')).toHaveValue('$.dependabot_alerts');
    expect(within(dialog).getByDisplayValue('state')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('fixed')).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          action_type: 'http_request',
          code: 'scan_github_code_inspection',
          name: 'GitHub 代码巡检',
          plugin_id: 'plugin_standard_github',
          request_config: expect.objectContaining({
            method: 'GET',
            path: '/repos/{{owner}}/{{repo}}/dependabot/alerts',
            query: expect.objectContaining({ per_page: 50, state: 'fixed' }),
          }),
          result_mapping: expect.objectContaining({
            findings_path: '$.dependabot_alerts',
            write_target: 'code_inspection_reports',
          }),
        }),
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增执行' }));
    const nextDialog = await findDialogByTitle('新增执行');
    fireEvent.mouseDown(within(nextDialog).getByLabelText('配置场景'));
    fireEvent.click(await screen.findByText('GitLab 代码巡检'));

    expect(within(nextDialog).getByLabelText('请求路径')).toHaveValue(
      '/api/{{api_version}}/projects/{{project_id}}/vulnerability_findings',
    );
    fireEvent.click(within(nextDialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies.at(-1)).toEqual(
        expect.objectContaining({
          action_type: 'http_request',
          code: 'scan_gitlab_code_inspection',
          name: 'GitLab 代码巡检',
          plugin_id: 'plugin_standard_gitlab',
          request_config: expect.objectContaining({
            method: 'GET',
            path: '/api/{{api_version}}/projects/{{project_id}}/vulnerability_findings',
            query: expect.objectContaining({ state: 'detected' }),
          }),
          result_mapping: expect.objectContaining({
            findings_path: '$.findings',
            write_target: 'code_inspection_reports',
          }),
        }),
      ),
    );
  });

  it('creates an official email notification action from the scene template', async () => {
    const { actionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行' }));
    fireEvent.click(screen.getByRole('button', { name: '新增执行' }));

    const dialog = await findDialogByTitle('新增执行');
    fireEvent.mouseDown(within(dialog).getByLabelText('配置场景'));
    fireEvent.click(await screen.findByText('邮箱通知发送'));

    expect(within(dialog).getByText('邮箱 (http)')).toBeInTheDocument();
    expect(within(dialog).getByText('生产邮箱网关 (prod)')).toBeInTheDocument();
    expect(within(dialog).getByText('POST')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('请求路径')).toHaveValue('/messages/send');
    expect(within(dialog).getByDisplayValue('Content-Type')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('application/json')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('to')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('{{default_to}}')).toBeInTheDocument();
    expect(within(dialog).getByText('邮件通知记录')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('收件人 JSONPath')).toHaveValue('$.recipients');
    expect(within(dialog).getByLabelText('主题 JSONPath')).toHaveValue('$.subject');
    expect(within(dialog).getByLabelText('投递状态 JSONPath')).toHaveValue('$.status');
    expect(within(dialog).getByLabelText('消息 ID JSONPath')).toHaveValue('$.message_id');

    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          action_type: 'http_request',
          code: 'send_email_notification',
          connection_id: 'connection_email_prod',
          name: '发送邮件通知',
          plugin_id: 'plugin_standard_email',
          request_config: expect.objectContaining({
            headers: { 'Content-Type': 'application/json' },
            method: 'POST',
            path: '/messages/send',
            query: expect.objectContaining({
              body_template: '{{result_summary}}',
              subject_template: '{{subject_template}}',
              to: '{{default_to}}',
            }),
          }),
          result_mapping: {
            delivery_id_path: '$.message_id',
            delivery_status_path: '$.status',
            recipients_path: '$.recipients',
            subject_path: '$.subject',
            write_target: 'email_notifications',
          },
        }),
      ]),
    );
  });

  it('shows write preview in action trial diagnostics', async () => {
    const { actionTrialBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行' }));
    fireEvent.click(await screen.findByText('试运行'));

    const dialog = await findDialogByTitle('执行试运行：调用反馈 API');
    fireEvent.click(within(dialog).getByRole('button', { name: '试运行' }));

    await waitFor(() =>
      expect(actionTrialBodies).toEqual([
        {
          connection_id: 'connection_maxcompute_prod',
          input_payload: {},
        },
      ]),
    );
    expect(await within(dialog).findByText('写入预览')).toBeInTheDocument();
    expect(within(dialog).getByText('写入目标：定时作业结果')).toBeInTheDocument();
    expect(within(dialog).getByText('预计写入：8')).toBeInTheDocument();
    expect(within(dialog).getByText('候选记录：0')).toBeInTheDocument();
    expect(within(dialog).getByText('预览值')).toBeInTheDocument();
  });
});
