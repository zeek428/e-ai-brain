import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import PluginsPage from '../src/pages/Plugins';
import { buildVisualRequestConfig } from '../src/pages/Plugins/components/pluginFormTransformHelpers';
import {
  ASSISTANT_DRAFT_RESOLUTION_STORAGE_KEY,
  ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY,
  ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY,
  ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY,
  assistantScopedStorageKey,
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
      (item) => within(item).queryAllByText(title).length > 0,
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

function removeSelectedTag(dialog: HTMLElement, label: string) {
  const tag = within(dialog).getByText(label).closest('.ant-select-selection-item');
  expect(tag).toBeTruthy();
  const removeButton = tag!.querySelector<HTMLElement>('.ant-select-selection-item-remove');
  expect(removeButton).toBeTruthy();
  fireEvent.mouseDown(removeButton!);
  fireEvent.click(removeButton!);
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
        name: '生产 MaxCompute 项目 请求动作',
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
      scheduled_job_sample_seed: {
        connection_id: 'connection_maxcompute_prod',
        next_step: 'copy_action_template_then_trial',
        plugin_connection_id: 'connection_maxcompute_prod',
        plugin_id: 'plugin_maxcompute',
        reuse_wizard: {
          can_continue: true,
          current_step_label: '连接测试样例',
          current_step: 'connection_test',
          blocked_steps: 0,
          completed_steps: 2,
          handoff_summary: [
            { key: 'request_preview', label: '最终请求', source: 'request_summary', status: 'ready' },
            { key: 'response_sample', label: '响应样例', source: 'response_summary', status: 'ready' },
            { key: 'action_template', label: '动作模板草案', source: 'connection_test', status: 'ready' },
          ],
          missing_requirements: [],
          next_action: 'copy_action_template_then_trial',
          next_action_description: '复制动作模板并自动使用连接测试响应样例试运行，生成写入预览。',
          pending_steps: 2,
          primary_action_label: '复制动作模板并试运行',
          progress_label: '2/4 步已就绪',
          progress_percent: 50,
          sample_source: 'connection_test_response',
          status: 'ready',
          steps: [
            { key: 'connection_test', label: '连接测试样例', source: 'connection_test_response', status: 'succeeded' },
            { key: 'action_trial', label: '动作写入预览', status: 'ready' },
            { key: 'scheduled_job_dry_run', label: '全链路试运行', status: 'pending' },
            { key: 'scheduled_job_config', label: '生成作业配置', status: 'pending' },
          ],
          total_steps: 4,
        },
        sample_source: 'connection_test_response',
        status: 'ready',
      },
      status: 'succeeded',
      test_history: [
        {
          action_template_draft: {
            action_type: 'http_request',
            code: 'test_connection_maxcompute_prod',
            connection_id: 'connection_maxcompute_prod',
            name: '生产 MaxCompute 项目 请求动作',
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
  options: {
    deferConnectionTest?: boolean;
    emptyActionTemplates?: boolean;
    includeOfficialActions?: boolean;
    includeDingTalkPlugins?: boolean;
    includeOfficialPlugins?: boolean;
    includeMultiResourceScheduledJob?: boolean;
    includeOutOfPageConnection?: boolean;
    includeProjectedPluginConnection?: boolean;
    failActionTrialWithApproval?: boolean;
  } = {},
) {
  const actionBodies: unknown[] = [];
  const actionDeleteIds: string[] = [];
  const actionListCalls: string[] = [];
  const actionTrialBodies: unknown[] = [];
  const actionUpdateBodies: unknown[] = [];
  const aiExecutorApprovalBodies: unknown[] = [];
  let aiExecutorApproved = false;
  const assistantDraftConfirmIds: string[] = [];
  const assistantDraftPatchBodies: unknown[] = [];
  const connectionBodies: unknown[] = [];
  const connectionDeleteIds: string[] = [];
  const connectionDiscoveryCalls: string[] = [];
  const connectionListCalls: string[] = [];
  const connectionUpdateBodies: unknown[] = [];
  const connectionTestCalls: string[] = [];
  const pluginCopyBodies: unknown[] = [];
  const pluginDeleteIds: string[] = [];
  const pluginUpdateBodies: unknown[] = [];
  const pluginObservabilityCalls: string[] = [];
  const runnerBodies: unknown[] = [];
  const runnerApprovalRequestBodies: unknown[] = [];
  const runnerDeleteIds: string[] = [];
  const runnerListCalls: string[] = [];
  const runnerPackageCalls: string[] = [];
  const runnerRotateBodies: unknown[] = [];
  const runnerTaskCancelBodies: unknown[] = [];
  const runnerTaskRetryBodies: unknown[] = [];
  const runnerTestCalls: string[] = [];
  const runnerTimeoutScanBodies: unknown[] = [];
  const runnerUpdateBodies: unknown[] = [];
  let runnerApprovalRequestApproved = false;
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
                template_version: 'v1',
                version_status: 'latest',
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
                template_version: 'v1',
                version_status: 'latest',
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
                template_version: 'v1',
                version_status: 'latest',
              },
              {
                category: 'business_system',
                code: 'internal_data_source',
                id: 'plugin_standard_internal_data_source',
                is_system: true,
                name: '内部数据源',
                protocol: 'internal_read_model',
                risk_level: 'low',
                status: 'active',
                template_version: 'v1',
                version_status: 'latest',
              },
              ...(options.includeDingTalkPlugins
                ? [
                    {
                      category: 'collaboration',
                      code: 'dingtalk_doc',
                      id: 'plugin_standard_dingtalk_doc',
                      is_system: true,
                      name: '钉钉文档',
                      protocol: 'mcp_streamable_http',
                      risk_level: 'high',
                      status: 'active',
                      template_version: 'v1',
                      version_status: 'latest',
                    },
                  ]
                : []),
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
                },
                auth_type: 'api_key_header',
                endpoint_url: 'http://gitlab.local',
                environment: 'prod',
                max_retries: 1,
                name: '生产 GitLab 连接',
                request_config: { query: {} },
                status: 'active',
                timeout_seconds: 30,
              },
              connection_schema: {
                schema_version: 'v1',
                sections: [
                  {
                    fields: [
                      {
                        description: '可选；仅当 GitLab API 动作需要默认 project_id/project_path 时填写。',
                        key: 'gitlab_project_url',
                        label: 'GitLab 地址',
                        managed_query_keys: ['api_version', 'group_id', 'project_id', 'project_path'],
                        placeholder: 'http://gitlab.local/acme/ai-brain.git',
                        required: false,
                        type: 'gitlab_project_url',
                      },
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
              latest_template_version: 'v1',
              name: 'GitLab',
              plugin_id: 'plugin_standard_gitlab',
              protocol: 'http',
              publisher: 'AI Brain 官方',
              recommended_scenarios: ['代码仓库质量巡检', '漏洞发现同步'],
              risk_level: 'medium',
              status: 'active',
              summary: '连接 GitLab API，读取项目、MR 和代码质量数据。',
              template_version: 'v1',
              upgrade_available: false,
              version_status: 'latest',
            },
            {
              action_count: 0,
              action_templates: ['GitHub 代码巡检', 'GitHub PR / 仓库读取'],
              category: 'devops',
              code: 'github',
              connection_defaults: {
                auth_config: {},
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
                  query: {},
                },
                status: 'active',
                timeout_seconds: 30,
              },
              connection_schema: {
                schema_version: 'v1',
                sections: [
                  {
                    fields: [
                      {
                        description: '可选；GitHub API 动作需要默认 owner/repo 时填写。',
                        key: 'repository_url',
                        label: '仓库地址',
                        managed_query_keys: ['owner', 'repo'],
                        required: false,
                        type: 'github_repository_url',
                      },
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
              latest_template_version: 'v1',
              name: 'GitHub',
              plugin_id: 'plugin_standard_github',
              protocol: 'http',
              publisher: 'AI Brain 官方',
              recommended_scenarios: ['代码仓库质量巡检', '安全告警同步'],
              risk_level: 'medium',
              status: 'active',
              summary: '连接 GitHub API，读取仓库、PR 和代码扫描数据。',
              template_version: 'v1',
              upgrade_available: false,
              version_status: 'latest',
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
              latest_template_version: 'v1',
              name: '邮箱',
              plugin_id: 'plugin_standard_email',
              protocol: 'http',
              publisher: 'AI Brain 官方',
              recommended_scenarios: ['代码巡检通知', '定时作业结果通知'],
              risk_level: 'medium',
              status: 'active',
              summary: '连接企业邮件网关或邮件 API。',
              template_version: 'v1',
              upgrade_available: false,
              version_status: 'latest',
            },
            {
              action_count: 0,
              action_templates: ['读取内部业务数据'],
              category: 'business_system',
              code: 'internal_data_source',
              connection_defaults: {
                auth_config: {},
                auth_type: 'none',
                endpoint_url: 'internal://e-ai-brain/business-data',
                environment: 'prod',
                max_retries: 0,
                name: '内部业务数据连接',
                request_config: {
	                  query: {
	                    field_mode: 'summary',
	                    limit: 100,
	                    source_types: ['user_insights', 'requirements', 'products', 'bugs'],
	                    window_end: '{{now}}',
	                    window_start: '{{current_date-30}}',
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
                      {
                        key: 'source_types',
                        label: '源数据',
                        options: [
                          { label: '用户洞察数据', value: 'user_insights' },
                          { label: '需求数据', value: 'requirements' },
                          { label: '产品数据', value: 'products' },
                          { label: 'Bug 数据', value: 'bugs' },
                        ],
                        path: 'request_config.query.source_types',
                        required: true,
                        type: 'multi_select',
                      },
                      {
                        key: 'field_mode',
                        label: '字段模式',
                        options: [
                          { label: '摘要字段', value: 'summary' },
                          { label: '完整字段', value: 'detail' },
                        ],
                        path: 'request_config.query.field_mode',
                        required: true,
                        type: 'select',
                      },
                      {
                        key: 'limit',
                        label: '每类最大行数',
                        path: 'request_config.query.limit',
                        required: true,
                        type: 'number',
                      },
	                      {
	                        key: 'window_start',
                        label: '开始时间',
                        path: 'request_config.query.window_start',
                        required: false,
                        supports_system_variables: true,
                        type: 'text',
                      },
                      {
                        key: 'window_end',
                        label: '结束时间',
                        path: 'request_config.query.window_end',
                        required: false,
                        supports_system_variables: true,
                        type: 'text',
                      },
                    ],
                    key: 'sources',
                    title: '源数据选择',
                  },
                  {
                    fields: [
                      {
                        key: 'requirements_status',
                        label: '需求状态',
                        options: [
                          { label: '草稿', value: 'draft' },
                          { label: '已排期', value: 'planned' },
                          { label: '已关闭', value: 'closed' },
                        ],
                        path: 'request_config.query.source_filters.requirements.status',
                        required: false,
                        type: 'select',
                        visible_when_source_types: ['requirements'],
                      },
                      {
                        key: 'requirements_priority',
                        label: '需求优先级',
                        options: [
                          { label: 'P0', value: 'P0' },
                          { label: 'P1', value: 'P1' },
                          { label: 'P2', value: 'P2' },
                        ],
                        path: 'request_config.query.source_filters.requirements.priority',
                        required: false,
                        type: 'select',
                        visible_when_source_types: ['requirements'],
                      },
                      {
                        key: 'bugs_status',
                        label: 'Bug 状态',
                        options: [
                          { label: '待处理', value: 'open' },
                          { label: '已关闭', value: 'closed' },
                        ],
                        path: 'request_config.query.source_filters.bugs.status',
                        required: false,
                        type: 'select',
                        visible_when_source_types: ['bugs'],
                      },
                      {
                        key: 'bugs_severity',
                        label: 'Bug 严重级别',
                        options: [
                          { label: 'critical', value: 'critical' },
                          { label: 'major', value: 'major' },
                        ],
                        path: 'request_config.query.source_filters.bugs.severity',
                        required: false,
                        type: 'select',
                        visible_when_source_types: ['bugs'],
                      },
                    ],
                    key: 'source_filters',
                    title: '按源过滤',
                  },
                ],
              },
              connection_count: 0,
              connection_template_version: 'v1',
              id: 'marketplace_internal_data_source',
              installed: true,
              is_system: true,
              latest_template_version: 'v1',
              name: '内部数据源',
              plugin_id: 'plugin_standard_internal_data_source',
              protocol: 'internal_read_model',
              publisher: 'AI Brain 官方',
              recommended_scenarios: ['每周内部业务洞察', '需求与 Bug 风险分析'],
              risk_level: 'low',
              status: 'active',
              summary: '只读读取 AI Brain 内部业务数据。',
              template_version: 'v1',
              upgrade_available: false,
              version_status: 'latest',
            },
            ...(options.includeDingTalkPlugins
              ? [
                  {
                    action_count: 0,
                    action_templates: [
                      '钉钉文档 - 搜索文档',
                      '钉钉文档 - 创建文档',
                      '钉钉文档 - 更新内容',
                    ],
                    authorization_guide: {
                      credential_reuse: {
                        example_refs: ['vault/dingtalk/shared/url_key', 'env:DINGTALK_MCP_KEY'],
                        supports_vault_ref: true,
                      },
                      subjects: [
                        { label: '个人授权', scenario: '个人访问自己的钉钉文档', type: 'user' },
                        { label: '系统授权', scenario: '团队共享巡检连接', type: 'system' },
                        { label: '应用授权', scenario: '企业应用统一接入', type: 'app' },
                      ],
                      url_key: {
                        query_key: 'key',
                        steps: [
                          '打开钉钉 MCP 市场能力详情',
                          '复制 StreamableHttp URL 或 JSON Config 中的 url',
                        ],
                        title: 'StreamableHttp URL 获取方式',
                      },
                    },
                    business_scenario_templates: [
                      {
                        code: 'dingtalk_knowledge_import',
                        name: '从钉钉文档/知识库导入知识',
                      },
                      {
                        code: 'dingtalk_inspection_bot_notice',
                        name: '巡检结果发钉钉机器人',
                      },
                      {
                        code: 'dingtalk_solution_doc_generation',
                        name: '生成方案文档到钉钉文档',
                      },
                    ],
                    capability_discovery: {
                      drift_policy: {
                        missing_tool: 'warn_disable_action',
                        new_tool: 'suggest_action_template',
                        schema_changed: 'mark_needs_review',
                      },
                      jsonrpc_method: 'tools/list',
                      known_tools: ['search_documents', 'get_document_content', 'create_document'],
                      mode: 'tools_list',
                    },
                    category: 'collaboration',
                    code: 'dingtalk_doc',
                    connection_defaults: {
                      auth_config: {
                        auth_subject_type: 'user',
                        query_key: 'key',
                        secret_ref: '',
                      },
                      auth_type: 'url_key',
                      endpoint_url: '',
                      environment: 'prod',
                      max_retries: 1,
                      name: '钉钉文档 MCP 连接',
                      request_config: {},
                      status: 'active',
                      timeout_seconds: 30,
                    },
                    connection_schema: {
                      schema_version: 'v1',
                      sections: [
                        {
                          fields: [
                            {
                              description: '个人授权填 user，企业统一授权填 system 或 app。',
                              key: 'auth_subject_type',
                              label: '授权主体',
                              options: [
                                { label: '个人授权', value: 'user' },
                                { label: '系统授权', value: 'system' },
                                { label: '应用授权', value: 'app' },
                              ],
                              path: 'auth_config.auth_subject_type',
                              required: true,
                              type: 'select',
                            },
                          ],
                          key: 'dingtalk_mcp',
                          title: '钉钉 MCP 授权',
                        },
                      ],
                    },
                    connection_count: 0,
                    connection_template_version: 'v1',
                    description: '连接钉钉文档 MCP。',
                    governance_policy: {
                      allowed_roles: ['admin', 'rd_owner', 'product_owner'],
                      high_risk_controls: [
                        'sensitive_read_audit',
                        'write_before_execute_review',
                        'notify_anti_mis_send',
                      ],
                      product_scope_required: true,
                    },
                    id: 'marketplace_dingtalk_doc',
                    installed: true,
                    is_system: true,
                    latest_template_version: 'v1',
                    name: '钉钉文档',
                    observability: {
                      health_dashboard: { enabled: true },
                      metrics: [
                        'success_rate',
                        'latency_p95_ms',
                        'failure_reason_distribution',
                        'key_expiry_alerts',
                        'action_trend',
                        'redacted_replay',
                      ],
                    },
                    plugin_id: 'plugin_standard_dingtalk_doc',
                    protocol: 'mcp_streamable_http',
                    publisher: '钉钉官方',
                    recommended_scenarios: ['读取项目文档', '创建协作文档'],
                    risk_level: 'high',
                    status: 'active',
                    summary: '通过钉钉官方 MCP 连接文档搜索、读取和创建能力。',
                    template_version: 'v1',
                    upgrade_available: false,
                    version_status: 'latest',
                  },
                ]
              : []),
          ],
          total: 4,
        },
      });
    }
    if (input === '/api/system/plugin-action-templates' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: options.emptyActionTemplates ? [] : [
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
            {
              action_type: 'internal_query',
              code: 'internal_business_data_query',
              default_code: 'query_internal_business_data',
              default_name: '读取内部业务数据',
              name: '读取内部业务数据',
              plugin_code: 'internal_data_source',
              request_config: { tool_name: 'internal_data_source.query' },
              result_mapping: { write_target: 'scheduled_job_result' },
              template_version: 'v1',
            },
            ...(options.includeDingTalkPlugins
              ? [
                  {
                    action_type: 'mcp_tool',
                    code: 'dingtalk_doc_update_content',
                    default_code: 'update_dingtalk_document_content',
                    default_name: '钉钉文档 - 更新内容',
                    form_defaults: {
                      content: '{{result_summary}}',
                      document_id: '',
                      mode: 'append',
                    },
                    name: '钉钉文档 - 更新内容',
                    plugin_code: 'dingtalk_doc',
                    request_config: {
                      mcp: {
                        mcp_id: '9629',
                        provider: 'dingtalk',
                        server_name: 'doc',
                      },
                      tool_name: 'update_document',
                    },
                    result_mapping: {
                      content_template: '{{result_summary}}',
                      document_id: '',
                      document_id_path: '$.document_id',
                      status_path: '$.status',
                      write_mode: 'append',
                      write_target: 'dingtalk_document',
                    },
                    risk_tier: 'write',
                    template_version: 'v1',
                  },
                ]
              : []),
          ],
          total: options.emptyActionTemplates ? 0 : options.includeDingTalkPlugins ? 5 : 4,
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
              mapping_fields: [],
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
            {
              code: 'dingtalk_document',
              default_result_mapping: {
                content_template: '{{result_summary}}',
                document_id: '',
                document_id_path: '$.document_id',
                status_path: '$.status',
                write_mode: 'append',
                write_target: 'dingtalk_document',
              },
              form_label: '钉钉文档',
              label: '钉钉文档',
              mapping_fields: [
                {
                  key: 'document_id',
                  label: '钉钉文档链接或 ID',
                  placeholder: 'https://alidocs.dingtalk.com/i/nodes/...',
                  required: true,
                },
                {
                  key: 'content_template',
                  label: '写入内容',
                  placeholder: '{{result_summary}}',
                  required: true,
                  type: 'textarea',
                },
                {
                  key: 'write_mode',
                  label: '写入方式',
                  options: [
                    { label: '追加内容', value: 'append' },
                    { label: '覆盖内容', value: 'overwrite' },
                  ],
                  placeholder: 'append',
                  required: true,
                  type: 'select',
                },
                {
                  key: 'document_id_path',
                  label: '返回文档 ID JSONPath',
                  placeholder: '$.document_id',
                  required: false,
                },
                {
                  key: 'status_path',
                  label: '返回状态 JSONPath',
                  placeholder: '$.status',
                  required: false,
                },
              ],
            },
          ],
          total: 5,
        },
      });
    }
    if (
      input === '/api/system/ai-executor-runners?page=1&page_size=10&sort_by=updated_at&sort_order=desc'
      && init?.method === 'GET'
    ) {
      runnerListCalls.push(String(input));
      return jsonResponse({
        data: {
          items: [
            {
              endpoint_url: 'model-gateway://default',
              executor_types: ['model_gateway'],
              heartbeat_timeout_seconds: 0,
              heartbeat_age_seconds: null,
              health_status: 'managed',
              id: 'ai_executor_runner_system_default',
              last_heartbeat_at: null,
              max_concurrent_tasks: 0,
              metadata: { is_system: true, managed_by: 'ai_brain' },
              name: '系统默认执行器',
              protocol: 'model_gateway',
              queue_summary: {
                available_slots: 0,
                failed_total: 0,
                max_concurrent_tasks: 0,
                queued: 0,
                running: 0,
                running_total: 0,
                total: 0,
              },
              readiness_summary: {
                attention_count: 0,
                blocked_count: 0,
                controls: [
                  {
                    key: 'managed_model_gateway',
                    label: '系统默认模型托管',
                    reason: '由平台模型网关托管执行，无需本地 Runner 心跳或 Token。',
                    required: true,
                    satisfied: true,
                    status: 'satisfied',
                  },
                  {
                    key: 'completion_callback',
                    label: '结果回写',
                    reason: '系统默认执行器直接写回运行结果和模型日志。',
                    required: true,
                    satisfied: true,
                    status: 'satisfied',
                  },
                ],
                missing_count: 0,
                readiness_status: 'ready',
                satisfied_count: 2,
                total: 2,
              },
              setup_command: '使用系统默认 AI 大模型执行，无需启动本地 Runner',
              status: 'active',
              token_configured: false,
              token_rotated_at: null,
              token_version: 0,
              workspace_roots: ['*'],
            },
            {
              endpoint_url: 'runner://local',
              executor_types: ['codex', 'claude', 'hermes', 'openclaw'],
              heartbeat_timeout_seconds: 120,
              heartbeat_age_seconds: 12,
              health_status: 'online',
              id: 'ai_executor_runner_001',
              last_heartbeat_at: '2026-06-13T09:00:00Z',
              latest_task_id: 'ai_executor_task_001',
              latest_task_status: 'running',
              max_concurrent_tasks: 1,
              metadata: {
                executor_commands: {
                  claude: 'claude',
                  codex: 'codex',
                  hermes: 'hermes',
                  openclaw: 'openclaw',
                },
                install_mode: 'launchd',
                package_arch: 'arm64',
                target_os: 'macos',
              },
              name: 'Zeek Mac 本地执行器',
              protocol: 'runner_polling',
              queue_summary: {
                available_slots: 0,
                failed_total: 1,
                latest_failure: {
                  error_code: 'AI_EXECUTOR_TASK_FAILED',
                  error_message: 'OpenClaw 命令执行失败',
                  id: 'ai_executor_task_failed',
                  status: 'failed',
                  updated_at: '2026-06-13T09:20:00Z',
                },
                max_concurrent_tasks: 1,
                queued: 2,
                running: 1,
                running_total: 1,
                succeeded: 5,
                total: 9,
              },
              readiness_summary: {
                attention_count: 1,
                blocked_count: 0,
                controls: [
                  {
                    key: 'protocol_adapter',
                    label: '协议适配',
                    reason: '当前 Runner 安装包和任务队列使用 polling 协议完成心跳、认领、日志和结果回写。',
                    required: true,
                    satisfied: true,
                    status: 'satisfied',
                  },
                  {
                    key: 'sandbox_permission_boundary',
                    label: '沙箱权限边界',
                    reason: '已启用命令白名单、禁用 shell、stdin 指令传递、进程组隔离、超时进程树清理、工作区白名单和高风险审批。',
                    required: true,
                    satisfied: true,
                    status: 'satisfied',
                  },
                ],
                missing_count: 0,
                readiness_status: 'attention',
                satisfied_count: 12,
                total: 13,
              },
              setup_command: 'ai-brain-runner start --runner-id ai_executor_runner_001 --token <runner_token> --server http://127.0.0.1:8000',
              status: 'active',
              token_configured: true,
              token_rotated_at: '2026-06-13T09:10:00Z',
              token_version: 2,
              workspace_roots: ['/Users/zeek/source/e-ai-brain'],
            },
            {
              endpoint_url: 'http://192.168.110.34:8000/api/system/ai-executor-runners',
              executor_types: ['codex'],
              heartbeat_timeout_seconds: 300,
              heartbeat_age_seconds: null,
              health_alert: {
                action_label: '启动 Runner',
                code: 'runner_never_connected',
                heartbeat_age_seconds: null,
                heartbeat_timeout_seconds: 300,
                message: 'Runner 尚未上报心跳，请启动本地 Runner 或检查安装包配置。',
                severity: 'warning',
              },
              health_status: 'never_connected',
              id: 'ai_executor_runner_cold',
              last_heartbeat_at: null,
              max_concurrent_tasks: 1,
              metadata: {
                install_mode: 'systemd',
                package_arch: 'amd64',
                target_os: 'linux',
              },
              name: '未连接 Runner',
              protocol: 'runner_polling',
              queue_summary: {
                available_slots: 1,
                failed_total: 0,
                max_concurrent_tasks: 1,
                queued: 0,
                running: 0,
                running_total: 0,
                total: 0,
              },
              readiness_summary: {
                attention_count: 2,
                blocked_count: 0,
                missing_count: 1,
                readiness_status: 'blocked',
                satisfied_count: 8,
                total: 12,
              },
              setup_command: 'ai-brain-runner start --runner-id ai_executor_runner_cold --token <runner_token> --server http://192.168.110.34:8000',
              status: 'active',
              token_configured: true,
              token_rotated_at: null,
              token_version: 1,
              workspace_roots: ['*'],
            },
          ],
          page: 1,
          page_size: 10,
          performance: {
            duration_ms: 8,
            p95_target_ms: 400,
            result_count: 3,
            slow: false,
            slow_threshold_ms: 400,
            total: 3,
          },
          total: 3,
        },
      });
    }
    if (String(input).startsWith('/api/system/ai-executor-runners/ai_executor_runner_001/install-package') && init?.method === 'GET') {
      runnerPackageCalls.push(String(input));
      return new Response(new Blob(['runner-package']), {
        headers: {
          'Content-Disposition': 'attachment; filename="ai-brain-runner-ai_executor_runner_001-macos-arm64-launchd.zip"',
          'Content-Type': 'application/zip',
        },
        status: 200,
      });
    }
    if (input === '/api/system/ai-executor-runners/ai_executor_runner_001/test' && init?.method === 'POST') {
      runnerTestCalls.push(String(input));
      return jsonResponse({
        data: {
          checked_at: '2026-06-13T09:30:00Z',
          diagnostics: [
            { detail: 'Runner 注册状态 active', name: 'runner_registration', status: 'succeeded' },
            { detail: 'Runner 心跳正常，12 秒前上报', name: 'runner_heartbeat', status: 'succeeded' },
          ],
          health_status: 'online',
          heartbeat_age_seconds: 12,
          latency_ms: 4,
          runner: {
            id: 'ai_executor_runner_001',
            name: 'Zeek Mac 本地执行器',
            protocol: 'runner_polling',
            token_configured: true,
          },
          runner_id: 'ai_executor_runner_001',
          status: 'succeeded',
        },
      });
    }
    if (
      input === '/api/system/ai-executor-approval-requests?status=pending&page=1&page_size=20&sort_by=updated_at&sort_order=desc'
      && init?.method === 'GET'
    ) {
      return jsonResponse({
        data: {
          items: runnerApprovalRequestApproved
            ? []
            : [
              {
                action_id: 'plugin_action_runner_push',
                approval: null,
                approval_request: {
                  approval_request_id: 'ai_executor_approval_request_001',
                  title: 'AI 执行器高风险操作审批',
                },
                blocked_operations: ['git_push'],
                connection_id: 'connection_runner_001',
                created_at: '2026-06-13T09:31:00Z',
                executor_type: 'codex',
                id: 'ai_executor_approval_request_001',
                requested_at: '2026-06-13T09:31:00Z',
                requested_by: 'admin',
                risk_level: 'high',
                runner_id: 'ai_executor_runner_001',
                status: 'pending',
                updated_at: '2026-06-13T09:31:00Z',
                workspace_root: '/Users/zeek/source/e-ai-brain',
              },
            ],
          page: 1,
          page_size: 20,
          total: runnerApprovalRequestApproved ? 0 : 1,
        },
      });
    }
    if (
      input === '/api/system/ai-executor-approval-requests/ai_executor_approval_request_001/approve'
      && init?.method === 'POST'
    ) {
      runnerApprovalRequestBodies.push(JSON.parse(String(init.body)));
      runnerApprovalRequestApproved = true;
      return jsonResponse({
        data: {
          action: null,
          approval: {
            approval_id: 'ai_executor_approval_request_001',
            approved: true,
            approved_by: 'admin',
            mode: 'platform_human_approval',
          },
          approval_request: {
            id: 'ai_executor_approval_request_001',
            status: 'approved',
          },
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
    if (input === '/api/system/ai-executor-runners/ai_executor_runner_001/rotate-token' && init?.method === 'POST') {
      runnerRotateBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({
        data: {
          id: 'ai_executor_runner_001',
          name: 'Zeek Mac 本地执行器',
          runner_token: 'runner-token-rotated',
          status: 'active',
          token_configured: true,
          token_rotated_at: '2026-06-13T09:20:00Z',
          token_version: 3,
        },
      });
    }
    if (input === '/api/system/ai-executor-tasks/ai_executor_task_001/logs' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          logs: [
            {
              level: 'info',
              message: 'checkout repository',
              sequence: 1,
              timestamp: '2026-06-13T09:11:00Z',
            },
            {
              level: 'info',
              message: 'scan started',
              sequence: 2,
              timestamp: '2026-06-13T09:11:10Z',
            },
          ],
          task: {
            id: 'ai_executor_task_001',
            runner_id: 'ai_executor_runner_001',
            scheduled_job_run_id: 'scheduled_job_run_runner_trace',
            status: 'running',
          },
        },
      });
    }
    if (input === '/api/system/ai-executor-tasks/ai_executor_task_001/cancel' && init?.method === 'POST') {
      runnerTaskCancelBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({
        data: {
          task: {
            error_code: 'AI_EXECUTOR_TASK_CANCELLED',
            id: 'ai_executor_task_001',
            runner_id: 'ai_executor_runner_001',
            status: 'cancelled',
          },
        },
      });
    }
    if (input === '/api/system/ai-executor-tasks/ai_executor_task_001/retry' && init?.method === 'POST') {
      runnerTaskRetryBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({
        data: {
          source_task: {
            error_code: 'AI_EXECUTOR_TASK_CANCELLED',
            id: 'ai_executor_task_001',
            runner_id: 'ai_executor_runner_001',
            scheduled_job_run_id: 'scheduled_job_run_runner_trace',
            status: 'cancelled',
          },
          task: {
            id: 'ai_executor_task_retry_001',
            logs: [
              {
                level: 'info',
                message: 'Task retried from ai_executor_task_001: 管理员从插件管理页面重试 Runner 任务',
                sequence: 1,
                timestamp: '2026-06-13T09:12:00Z',
              },
            ],
            request_config: {
              retry_history: [
                {
                  reason: '管理员从插件管理页面重试 Runner 任务',
                  source_status: 'cancelled',
                  source_task_id: 'ai_executor_task_001',
                },
              ],
              retry_of_task_id: 'ai_executor_task_001',
            },
            runner_id: 'ai_executor_runner_001',
            scheduled_job_run_id: 'scheduled_job_run_runner_trace',
            status: 'queued',
          },
        },
      });
    }
    if (input === '/api/system/ai-executor-tasks/timeout-scan' && init?.method === 'POST') {
      runnerTimeoutScanBodies.push(JSON.parse(String(init.body ?? '{}')));
      return jsonResponse({
        data: {
          dead_letter_task_ids: [],
          next_actions: [
            {
              description: '等待 Runner 重新认领并继续执行任务。',
              key: 'watch_requeued_tasks',
              label: '等待 Runner 重新认领',
              severity: 'warning',
              task_ids: ['ai_executor_task_001'],
            },
          ],
          requeued_task_ids: ['ai_executor_task_001'],
          summary: {
            dead_letter_count: 0,
            manual_attention_required: false,
            message: '已重派 1 个 Runner 任务，等待 Runner 重新认领。',
            requeued_count: 1,
            scanned_at: '2026-06-13T09:35:00Z',
            status: 'requeued',
            timed_out_count: 0,
            total_affected: 1,
          },
          tasks: [
            {
              id: 'ai_executor_task_001',
              runner_id: 'ai_executor_runner_001',
              scheduled_job_run_id: 'scheduled_job_run_runner_trace',
              status: 'queued',
            },
          ],
          timed_out_task_ids: [],
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
    if (input === '/api/system/plugins/plugin_standard_github/copy' && init?.method === 'POST') {
      pluginCopyBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({
        data: {
          category: 'devops',
          code: 'github_custom',
          id: 'plugin_github_custom',
          is_system: false,
          name: 'GitHub 副本',
          protocol: 'http',
          risk_level: 'medium',
          source_plugin_id: 'plugin_standard_github',
          status: 'active',
          template_version: 'v1',
          version_status: 'custom',
        },
      });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/system/plugin-connections')
      && init?.method === 'GET'
    ) {
      connectionListCalls.push(input);
      const baseConnections = [
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
      ];
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
            ...(options.includeDingTalkPlugins
              ? [
                  {
                    auth_config: {
                      query_key: 'key',
                      secret_ref: '***',
                    },
                    auth_type: 'url_key',
                    endpoint_url: 'https://mcp-gw.dingtalk.com/server/doc-instance-123',
                    environment: 'prod',
                    id: 'connection_dingtalk_doc',
                    name: '钉钉文档个人授权',
                    plugin_code: 'dingtalk_doc',
                    plugin_id: 'plugin_standard_dingtalk_doc',
                    plugin_name: '钉钉文档',
                    request_config: {},
                    status: 'active',
                  },
                ]
              : []),
          ]
        : [];
      const outOfPageConnections = options.includeOutOfPageConnection
        ? [
            {
              auth_type: 'none',
              endpoint_url: 'https://ai-service.example.com/chat-records',
              environment: 'prod',
              id: 'connection_ai_chat_records',
              name: 'AI 客服聊天记录连接',
              plugin_id: 'plugin_maxcompute',
              request_config: {
                headers: { 'Content-Type': 'application/json' },
                query: { start_date: '{{current_date-7}}' },
              },
              status: 'active',
            },
          ]
        : [];
      const projectedPluginConnections = options.includeProjectedPluginConnection
        ? [
            {
              auth_type: 'none',
              endpoint_url: 'https://feedback.example.com/api',
              environment: 'prod',
              id: 'connection_projected_plugin_name',
              name: '用户反馈连接器',
              plugin_code: 'generic_http',
              plugin_id: 'plugin_001',
              plugin_name: '通用 HTTP 插件',
              request_config: {
                headers: { Authorization: 'APPCODE 208b5b1456ee445ca47a42c' },
                query: { start_pt: '{{current_date-7}}' },
              },
              status: 'active',
            },
          ]
        : [];
      const allConnections = [
        ...baseConnections,
        ...officialConnections,
        ...outOfPageConnections,
        ...projectedPluginConnections,
      ];
      const isPagedRequest = input.includes('page=') || input.includes('page_size=');
      const pageConnections = [
        ...baseConnections,
        ...officialConnections,
        ...projectedPluginConnections,
      ];
      return jsonResponse({
        data: {
          items: isPagedRequest ? pageConnections : allConnections,
          total: allConnections.length,
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
    if (input === '/api/system/plugin-connections/connection_created/test' && init?.method === 'POST') {
      connectionTestCalls.push(String(input));
      return jsonResponse({
        data: {
          ...pluginConnectionTestBody().data,
          connection_id: 'connection_created',
        },
      });
    }
    if (input === '/api/system/plugin-connections/connection_dingtalk_doc/discover-tools' && init?.method === 'POST') {
      connectionDiscoveryCalls.push(String(input));
      return jsonResponse({
        data: {
          discovered_tools: [
            { name: 'search_documents' },
            { name: 'create_document' },
            { name: 'export_document' },
          ],
          missing_tools: ['get_document_content'],
          new_tools: ['export_document'],
          request_summary: {
            method: 'POST',
            query: { key: '***', provider: 'dingtalk' },
          },
          schema_changed_tools: ['create_document'],
          status: 'drift_detected',
          suggestions: [
            { detail: '新增工具 export_document 可生成动作模板', type: 'suggest_action_template' },
          ],
          tool_count: 3,
        },
      });
    }
    if (input === '/api/system/plugin-observability?provider=dingtalk' && init?.method === 'GET') {
      pluginObservabilityCalls.push(String(input));
      return jsonResponse({
        data: {
          action_trend: [{ action_code: 'read_dingtalk_doc', count: 2 }],
          failure_reason_distribution: [{ count: 1, reason: 'HTTPError' }],
          key_expiry_alerts: [{ connection_id: 'connection_dingtalk_doc', days_left: 8 }],
          provider: 'dingtalk',
          redacted_recent_replays: [
            {
              request_preview: {
                query: { key: '***', provider: 'dingtalk' },
                tool_name: 'get_document_content',
              },
            },
          ],
          summary: {
            latency_p95_ms: 360,
            success_rate: 0.5,
            total_invocations: 2,
          },
        },
      });
    }
    if (
      typeof input === 'string'
      && input.startsWith('/api/system/plugin-actions')
      && init?.method === 'GET'
    ) {
      actionListCalls.push(input);
      const officialActions = options.includeOfficialActions
        ? [
            {
              action_type: 'http_request',
              code: 'scan_github_code_inspection',
              connection_id: null,
              id: 'action_github_code_inspection',
              name: 'GitHub 代码巡检',
              plugin_id: 'plugin_standard_github',
              request_config: {
                method: 'GET',
                path: '/repos/{{owner}}/{{repo}}/dependabot/alerts',
                query: { state: 'fixed', per_page: 50 },
              },
              requires_human_review: false,
              result_mapping: {
                findings_path: '$.dependabot_alerts',
                write_target: 'code_inspection_reports',
              },
              status: 'active',
            },
          ]
        : [];
      const dingtalkDocumentActions = options.includeDingTalkPlugins
        ? [
            {
              action_type: 'mcp_tool',
              code: 'update_dingtalk_document_content',
              connection_id: 'connection_dingtalk_doc',
              id: 'action_dingtalk_doc_update',
              name: '钉钉文档 - 更新内容',
              plugin_id: 'plugin_standard_dingtalk_doc',
              request_config: {
                arguments: {
                  format: 'markdown',
                  markdown: '{{result_summary}}',
                  mode: 'append',
                  nodeId: 'b9Y4gmKWrekkKx2ET4dzY39d8GXn6lpz',
                },
                mcp: { provider: 'dingtalk', server_name: 'doc' },
                tool_name: 'update_document',
              },
              requires_human_review: false,
              result_mapping: {
                content_template: '{{result_summary}}',
                document_id: 'b9Y4gmKWrekkKx2ET4dzY39d8GXn6lpz',
                document_id_path: '$.document_id',
                status_path: '$.status',
                write_mode: 'append',
                write_target: 'dingtalk_document',
              },
              status: 'active',
            },
          ]
        : [];
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
            ...dingtalkDocumentActions,
            ...officialActions,
          ],
          total: 1 + dingtalkDocumentActions.length + officialActions.length,
        },
      });
    }
    if (input === '/api/system/scheduled-jobs' && init?.method === 'GET') {
      const items = options.includeMultiResourceScheduledJob
        ? [
            {
              id: 'scheduled_job_multi_plugin_usage',
              job_type: 'plugin_action_invoke',
              name: '多连接插件巡检',
              plugin_action_id: null,
              plugin_action_ids: ['action_feedback_api'],
              plugin_connection_id: null,
              plugin_connection_ids: ['connection_maxcompute_prod'],
              schedule_type: 'manual',
              status: 'active',
            },
          ]
        : [];
      return jsonResponse({ data: { items, total: items.length } });
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
    if (
      typeof input === 'string'
      && input.startsWith('/api/assistant/action-drafts/')
      && !input.endsWith('/confirm')
      && init?.method === 'PATCH'
    ) {
      const body = JSON.parse(String(init.body));
      assistantDraftPatchBodies.push(body);
      return jsonResponse({
        data: {
          action: String(body.payload?.plugin_id ?? '').includes('github')
            ? 'create_plugin_action'
            : 'create_plugin_connection',
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
      const isConnectionDraft = draftId.includes('connection');
      return jsonResponse({
        data: {
          draft: {
            action: isConnectionDraft ? 'create_plugin_connection' : 'create_plugin_action',
            id: draftId,
            payload: {},
            status: 'confirmed',
            title: 'AI 助手草案',
          },
          run: {
            action: isConnectionDraft ? 'create_plugin_connection' : 'create_plugin_action',
            draft_id: draftId,
            id: `assistant_action_run_${assistantDraftConfirmIds.length}`,
            result: {
              id: isConnectionDraft ? 'connection_created' : 'action_maxcompute_weekly',
            },
            result_id: isConnectionDraft ? 'connection_created' : 'action_maxcompute_weekly',
            result_type: isConnectionDraft ? 'plugin_connection' : 'plugin_action',
            status: 'succeeded',
          },
        },
      });
    }
    if (input === '/api/system/plugin-actions' && init?.method === 'POST') {
      actionBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'action_maxcompute_weekly', status: 'active' } });
    }
    if (input === '/api/system/plugin-actions/action_feedback_api' && init?.method === 'PATCH') {
      actionUpdateBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'action_feedback_api', status: 'active' } });
    }
    if (
      input === '/api/system/plugin-actions/action_feedback_api/ai-executor-approval'
      && init?.method === 'POST'
    ) {
      const body = JSON.parse(String(init.body));
      aiExecutorApprovalBodies.push(body);
      aiExecutorApproved = true;
      return jsonResponse({
        data: {
          action: {
            action_type: 'mcp_tool',
            code: 'fetch_feedback_api',
            connection_id: 'connection_maxcompute_prod',
            id: 'action_feedback_api',
            name: '调用反馈 API',
            plugin_id: 'plugin_standard_ai_executor',
            request_config: {
              ai_executor_approval: {
                approval_id: 'ai_executor_approval_001',
                approval_request_id: body.approval_request?.approval_request_id,
                approved: true,
                approved_at: '2026-07-02T10:00:00+00:00',
                approved_by: 'user_admin',
                approved_operations: ['git_push_or_merge'],
                expires_at: '2026-07-02T11:00:00+00:00',
                mode: 'platform_human_approval',
                policy_version: 'runner_safety_v1',
                reason: body.reason,
              },
              instruction: '完成检查后执行 git push origin main。',
            },
            requires_human_review: true,
            result_mapping: { write_target: 'scheduled_job_result' },
            status: 'active',
          },
          approval: {
            approval_id: 'ai_executor_approval_001',
            approved: true,
            approved_operations: ['git_push_or_merge'],
          },
        },
      });
    }
    if (input === '/api/system/plugin-actions/action_feedback_api' && init?.method === 'DELETE') {
      actionDeleteIds.push('action_feedback_api');
      return jsonResponse({ data: { deleted: true, id: 'action_feedback_api' } });
    }
    const actionTrialMatch = String(input).match(/^\/api\/system\/plugin-actions\/([^/]+)\/trial$/);
    if (actionTrialMatch && init?.method === 'POST') {
      const requestBody = JSON.parse(String(init.body));
      actionTrialBodies.push(requestBody);
      const actionId = actionTrialMatch[1];
      if (options.failActionTrialWithApproval && !aiExecutorApproved) {
        return jsonResponse({
          data: {
            action_id: actionId,
            connection_id: 'connection_maxcompute_prod',
            error_code: 'AI_EXECUTOR_APPROVAL_REQUIRED',
            error_detail: {
              approval_request: {
                approval_request_id: 'ai_executor_approval_request_001',
                approval_template: {
                  approved: true,
                  approved_operations: ['git_push_or_merge'],
                  mode: 'platform_human_approval',
                  policy_version: 'runner_safety_v1',
                },
                blocked_operations: ['git_push_or_merge'],
                next_action: 'create_platform_human_approval',
                required_fields: [
                  'approval_id',
                  'approved',
                  'approved_at',
                  'approved_by',
                  'approved_operations',
                  'expires_at',
                  'mode',
                  'policy_version',
                ],
                status: 'approval_required',
                title: 'AI 执行器高风险操作审批',
              },
            },
            error_message: 'AI executor instruction requires human approval before Runner dispatch',
            latency_ms: 8,
            mapping_hits: [],
            plugin_id: 'plugin_standard_ai_executor',
            request_preview: { method: 'MCP', tool_name: 'ai_executor.run_instruction' },
            response_summary: {},
            sample_source: 'action_trial_response',
            scheduled_job_dry_run_seed: {
              connection_id: 'connection_maxcompute_prod',
              input_payload: requestBody.input_payload ?? {},
              plugin_action_id: actionId,
              plugin_connection_id: 'connection_maxcompute_prod',
              plugin_input_mapping: requestBody.input_payload ?? {},
              plugin_output_mapping: { write_target: 'scheduled_job_result' },
              response_summary: {},
              reuse_wizard: {
                can_continue: false,
                current_step: 'action_trial',
                current_step_label: '动作写入预览',
                blocked_steps: 1,
                completed_steps: 1,
                draft_payload_ready: false,
                handoff_summary: [
                  { key: 'response_sample', label: '响应样例', source: 'not_available', status: 'missing' },
                  { key: 'input_mapping', label: '连接输入映射', source: 'trial_input_payload', status: 'missing' },
                  { key: 'output_mapping', label: '结果映射', source: 'plugin_action_result_mapping', status: 'missing' },
                  { key: 'write_preview', label: '写入预览', source: 'not_available', status: 'missing' },
                ],
                missing_requirements: ['action_trial_succeeded', 'action_trial_response', 'write_preview'],
                next_action: 'fix_action_trial',
                next_action_description: '先修复动作试运行，确保响应样例和写入预览都可用。',
                pending_steps: 2,
                primary_action_label: '修复动作试运行',
                progress_label: '1/4 步已就绪',
                progress_percent: 25,
                sample_source: 'action_trial_response',
                status: 'blocked',
                steps: [
                  { key: 'connection_test', label: '连接测试样例', source: 'action_trial_response', status: 'not_used' },
                  { key: 'action_trial', label: '动作写入预览', source: 'action_trial_response', status: 'failed' },
                  { key: 'scheduled_job_dry_run', label: '全链路试运行', status: 'pending' },
                  { key: 'scheduled_job_config', label: '生成作业配置', status: 'pending' },
                ],
                total_steps: 4,
              },
              sample_source: 'action_trial_response',
              write_preview: {},
            },
            status: 'failed',
            write_preview: undefined,
          },
        });
      }
      const responseSummary = requestBody.sample_response_summary ?? { json: { commits: 8 } };
      const previewValue = responseSummary?.json?.commits ?? 8;
      const sampleSource = requestBody.sample_response_summary
        ? 'connection_test_response'
        : 'action_trial_response';
      return jsonResponse({
        data: {
          action_id: actionId,
          connection_id: 'connection_maxcompute_prod',
          latency_ms: 12,
          mapping_hits: [
            {
              key: 'records_imported_path',
              matched: true,
              path: '$.commits',
              value_preview: previewValue,
            },
          ],
          plugin_id: 'plugin_maxcompute',
          request_preview: {
            method: 'GET',
            query: { start_pt: '20260604' },
            url: 'https://ai-brain-maxcompute-mcp.internal/mcp?start_pt=20260604',
          },
          response_summary: responseSummary,
          sample_source: sampleSource,
          scheduled_job_dry_run_seed: {
            connection_id: 'connection_maxcompute_prod',
            input_payload: requestBody.input_payload ?? {},
            plugin_action_id: actionId,
            plugin_connection_id: 'connection_maxcompute_prod',
            plugin_input_mapping: requestBody.input_payload ?? {},
            plugin_output_mapping: { records_imported_path: '$.commits', write_target: 'scheduled_job_result' },
            response_summary: responseSummary,
            reuse_wizard: {
              can_continue: true,
              current_step_label: '动作写入预览',
              current_step: 'action_trial',
              blocked_steps: 0,
              completed_steps: 4,
              handoff_summary: [
                { key: 'response_sample', label: '响应样例', source: sampleSource, status: 'ready' },
                { key: 'input_mapping', label: '连接输入映射', source: 'trial_input_payload', status: 'ready' },
                { key: 'output_mapping', label: '结果映射', source: 'plugin_action_result_mapping', status: 'ready' },
                { key: 'write_preview', label: '写入预览', source: sampleSource, status: 'ready' },
              ],
              missing_requirements: [],
              next_action: 'create_scheduled_job_draft',
              next_action_description: '生成定时作业草稿，并带入连接、动作、映射、响应样例和写入预览。',
              pending_steps: 0,
              primary_action_label: '生成定时作业草稿',
              progress_label: '4/4 步已就绪',
              progress_percent: 100,
              sample_source: sampleSource,
              status: 'ready',
              steps: [
                {
                  key: 'connection_test',
                  label: '连接测试样例',
                  source: sampleSource,
                  status: sampleSource === 'connection_test_response' ? 'succeeded' : 'not_used',
                },
                { key: 'action_trial', label: '动作写入预览', source: sampleSource, status: 'succeeded' },
                { key: 'scheduled_job_dry_run', label: '全链路试运行', status: 'ready' },
                { key: 'scheduled_job_config', label: '生成作业配置', status: 'ready' },
              ],
              total_steps: 4,
            },
            sample_source: sampleSource,
            write_preview: {
              candidate_count: 0,
              preview_value: previewValue,
              records_imported: previewValue,
              sample_records: [],
              write_target: 'scheduled_job_result',
              write_target_label: '定时作业结果',
            },
          },
          status: 'succeeded',
          write_preview: {
            candidate_count: 0,
            preview_value: previewValue,
            records_imported: previewValue,
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
    actionListCalls,
    actionTrialBodies,
    actionUpdateBodies,
    aiExecutorApprovalBodies,
    assistantDraftConfirmIds,
    assistantDraftPatchBodies,
    connectionBodies,
    connectionDeleteIds,
    connectionDiscoveryCalls,
    connectionListCalls,
    connectionTestCalls,
    connectionUpdateBodies,
    fetchMock,
    pluginDeleteIds,
    pluginCopyBodies,
    pluginObservabilityCalls,
    pluginUpdateBodies,
    resolveConnectionTest: () => {
      connectionTestDeferred?.resolve(jsonResponse(pluginConnectionTestBody()));
    },
    runnerBodies,
    runnerApprovalRequestBodies,
    runnerDeleteIds,
    runnerListCalls,
    runnerPackageCalls,
    runnerRotateBodies,
    runnerTaskCancelBodies,
    runnerTaskRetryBodies,
    runnerTestCalls,
    runnerTimeoutScanBodies,
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

    expect(screen.queryByRole('heading', { name: '插件管理' })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: '新增插件' }));

    const dialog = await findDialogByTitle('新增插件');
    expect(within(dialog).queryByRole('textbox', { name: '分类' })).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('分类'));
    expect((await screen.findAllByText('数据仓库 / BI')).length).toBeGreaterThan(0);
    expect(screen.getByText('DevOps / 代码平台')).toBeInTheDocument();
    expect(screen.getByText('日志 / 监控')).toBeInTheDocument();
  });

  it('keeps plugin management focused on configuration instead of invocation logs', async () => {
    const { fetchMock } = installPluginsFetchMock();

    render(<PluginsPage />);

    expect(await screen.findByRole('tab', { name: '插件' })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: '调用日志' })).not.toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock).not.toHaveBeenCalledWith('/api/system/plugin-invocation-logs', expect.anything()),
    );
  });

  it('names plugin actions as actions while keeping AI executors distinct', async () => {
    installPluginsFetchMock();

    render(<PluginsPage />);

    expect(await screen.findByRole('tab', { name: '动作' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: '执行器' })).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: '执行' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: '动作' }));
    expect(await screen.findByRole('button', { name: '新增动作' })).toBeInTheDocument();
  });

  it('keeps plugin management compact while retaining system variable insertion in forms', async () => {
    installPluginsFetchMock();

    render(<PluginsPage />);

    expect(await screen.findByRole('tab', { name: '动作' })).toBeInTheDocument();
    expect(screen.queryByText('系统变量预览')).not.toBeInTheDocument();
    expect(screen.queryByText('常用变量')).not.toBeInTheDocument();
    expect(screen.queryByText('通用调用链路')).not.toBeInTheDocument();
    expect(screen.queryByText('当前解析值')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await findDialogByTitle('新增动作');
    fireEvent.click(within(dialog).getByRole('button', { name: /添加 Params/ }));
    fireEvent.mouseDown(within(dialog).getByText('系统变量'));

    expect(await screen.findByText('当前日期 - 7 天')).toBeInTheDocument();
  });

  it('manages AI executor runners with remote executor options and install packages', async () => {
    const { runnerBodies, runnerListCalls, runnerPackageCalls } = installPluginsFetchMock();
    const createObjectURL = vi.fn(() => 'blob:ai-brain-runner');
    const revokeObjectURL = vi.fn();
    const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行器' }));

    expect(await screen.findByText('AI 执行器')).toBeInTheDocument();
    expect(runnerListCalls).toEqual([
      '/api/system/ai-executor-runners?page=1&page_size=10&sort_by=updated_at&sort_order=desc',
    ]);
    expect(screen.getByText('查询 8ms')).toBeInTheDocument();
    expect(screen.getByText('Zeek Mac 本地执行器')).toBeInTheDocument();
    expect(screen.getByText('online')).toBeInTheDocument();
    expect(screen.getByText('就绪 attention')).toBeInTheDocument();
    const runnerExpandButtons = Array.from(
      document.querySelectorAll<HTMLElement>('.ant-table-row-expand-icon'),
    );
    expect(runnerExpandButtons.length).toBeGreaterThanOrEqual(2);
    fireEvent.click(runnerExpandButtons[1]);
    expect(await screen.findByText('运行就绪清单')).toBeInTheDocument();
    expect(screen.getByText('协议适配 · satisfied')).toBeInTheDocument();
    expect(screen.getByText('沙箱权限边界 · satisfied')).toBeInTheDocument();
    expect(screen.getByText('未连接 Runner')).toBeInTheDocument();
    expect(screen.getByText('never_connected')).toBeInTheDocument();
    expect(screen.getByText('就绪 blocked')).toBeInTheDocument();
    expect(screen.getByText('Runner 尚未上报心跳，请启动本地 Runner 或检查安装包配置。')).toBeInTheDocument();
    expect(screen.getAllByText('排队 2').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('运行中 1').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('异常 1').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('可用槽 0').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('最近失败：OpenClaw 命令执行失败')).toBeInTheDocument();
    expect(screen.getAllByText('ai-brain-runner start --runner-id ai_executor_runner_001 --token <runner_token> --server http://127.0.0.1:8000').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Codex').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Claude Code')).toBeInTheDocument();
    expect(screen.getByText('Hermes')).toBeInTheDocument();
    expect(screen.getByText('OpenClaw')).toBeInTheDocument();
    expect(screen.getByText('/Users/zeek/source/e-ai-brain')).toBeInTheDocument();
    expect(screen.getByText('2026-06-13 17:00')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '下载安装包 Zeek Mac 本地执行器' }));
    await waitFor(() =>
      expect(runnerPackageCalls).toEqual([
        '/api/system/ai-executor-runners/ai_executor_runner_001/install-package?target_os=macos&arch=arm64&install_mode=launchd',
      ]),
    );
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(anchorClick).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: '新增执行器' }));

    const dialog = await findDialogByTitle('新增执行器');
    expect(within(dialog).getByText(
      '当前本地 Runner 安装包和任务队列闭环使用 Runner Polling；WebSocket/MCP 为预留协议。',
    )).toBeInTheDocument();
    fireEvent.change(within(dialog).getByLabelText('名称'), {
      target: { value: '本地 OpenClaw 执行器' },
    });
    fireEvent.change(within(dialog).getByLabelText('Codex 命令'), {
      target: { value: 'codex --profile ai-brain' },
    });
    fireEvent.change(within(dialog).getByLabelText('Claude Code 命令'), {
      target: { value: 'claude' },
    });
    fireEvent.change(within(dialog).getByLabelText('Hermes 命令'), {
      target: { value: 'hermes' },
    });
    fireEvent.change(within(dialog).getByLabelText('OpenClaw 命令'), {
      target: { value: 'openclaw' },
    });
    fireEvent.click(within(dialog).getByRole('switch', { name: '部署执行能力' }));
    expect(within(dialog).getByLabelText('目标系统')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('CPU 架构')).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(runnerBodies).toEqual([
        expect.objectContaining({
          capabilities: ['deployment'],
          executor_types: ['codex', 'openclaw'],
          metadata: expect.objectContaining({
            executor_commands: {
              claude: 'claude',
              codex: 'codex --profile ai-brain',
              hermes: 'hermes',
              openclaw: 'openclaw',
            },
            install_mode: 'systemd',
            package_arch: 'amd64',
            target_os: 'linux',
          }),
          name: '本地 OpenClaw 执行器',
          protocol: 'runner_polling',
          workspace_roots: ['/Users/zeek/source/e-ai-brain'],
        }),
      ]),
    );
    expect(await screen.findByText('runner-token-created')).toBeInTheDocument();
  });

  it('shows the system default executor as a managed read-only executor', async () => {
    installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行器' }));

    expect(await screen.findByText('系统默认执行器')).toBeInTheDocument();
    expect(screen.getAllByText('model_gateway').length).toBeGreaterThan(0);
    expect(screen.getByText('managed')).toBeInTheDocument();
    expect(screen.getByText('就绪 ready')).toBeInTheDocument();
    expect(screen.getByText('使用系统默认 AI 大模型执行，无需启动本地 Runner')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '测试执行器 系统默认执行器' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '测试执行器 Zeek Mac 本地执行器' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '编辑执行器 系统默认执行器' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '删除执行器 系统默认执行器' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '轮换 Token 系统默认执行器' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '查看执行日志 系统默认执行器' })).not.toBeInTheDocument();
  });

  it('can test an AI executor runner from the runner list', async () => {
    const { runnerTestCalls } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行器' }));

    fireEvent.click(await screen.findByRole('button', { name: '测试执行器 Zeek Mac 本地执行器' }));

    await waitFor(() =>
      expect(runnerTestCalls).toEqual(['/api/system/ai-executor-runners/ai_executor_runner_001/test']),
    );
    const dialog = await findDialogByTitle('执行器测试诊断');
    expect(within(dialog).getByText('Zeek Mac 本地执行器')).toBeInTheDocument();
    expect(within(dialog).getByText('Runner 心跳正常，12 秒前上报')).toBeInTheDocument();
  });

  it('shows and approves pending AI executor approval requests from the runner list', async () => {
    const { runnerApprovalRequestBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行器' }));
    fireEvent.click(await screen.findByRole('button', { name: '查看执行器审批请求' }));

    const dialog = await findDialogByTitle('AI 执行器审批请求');
    expect(within(dialog).getByText('AI 执行器高风险操作审批')).toBeInTheDocument();
    expect(within(dialog).getByText('ai_executor_approval_request_001')).toBeInTheDocument();
    expect(within(dialog).getByText('git_push')).toBeInTheDocument();
    expect(within(dialog).getByText('工作区：/Users/zeek/source/e-ai-brain')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: '审批请求 ai_executor_approval_request_001' }));

    await waitFor(() =>
      expect(runnerApprovalRequestBodies).toEqual([
        { reason: '管理员从插件管理执行器页审批放行' },
      ]),
    );
    expect(await screen.findByText('审批请求已放行')).toBeInTheDocument();
  });

  it('rotates runner tokens and shows streaming task logs with cancellation', async () => {
    const {
      runnerRotateBodies,
      runnerTaskCancelBodies,
      runnerTaskRetryBodies,
      runnerTimeoutScanBodies,
    } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '执行器' }));

    expect(await screen.findByText('Token v2')).toBeInTheDocument();
    expect(screen.getByText('2026-06-13 17:10')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '超时扫描' }));
    await waitFor(() => expect(runnerTimeoutScanBodies).toEqual([{}]));
    const timeoutDialog = await findDialogByTitle('Runner 超时扫描');
    expect(within(timeoutDialog).getByText('重派 1')).toBeInTheDocument();
    expect(within(timeoutDialog).getByText('等待 Runner 重新认领')).toBeInTheDocument();
    expect(within(timeoutDialog).getByText('已重派 1 个 Runner 任务，等待 Runner 重新认领。')).toBeInTheDocument();
    fireEvent.click(within(timeoutDialog).getByRole('button', { name: /知道了|OK|确\s*定/ }));

    fireEvent.click(screen.getByRole('button', { name: '轮换 Token Zeek Mac 本地执行器' }));
    const rotateDialog = await findDialogByTitle('轮换 Runner Token');
    fireEvent.click(within(rotateDialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() => expect(runnerRotateBodies).toEqual([{}]));
    expect(await screen.findByText('runner-token-rotated')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '查看执行日志 Zeek Mac 本地执行器' }));
    const logDrawer = await screen.findByRole('dialog', { name: 'Runner 执行日志' });
    expect(within(logDrawer).getByText('ai_executor_task_001')).toBeInTheDocument();
    expect(within(logDrawer).getByRole('link', { name: '任务诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=ai_executor_task_001&source_type=ai_executor_task',
    );
    expect(within(logDrawer).getByRole('link', { name: 'Runner 诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=ai_executor_runner_001&source_type=ai_executor_runner',
    );
    expect(within(logDrawer).getByRole('link', { name: '来源运行诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=scheduled_job_run_runner_trace&source_type=scheduled_job_run',
    );
    expect(within(logDrawer).getByText('checkout repository')).toBeInTheDocument();
    expect(within(logDrawer).getByText('scan started')).toBeInTheDocument();
    expect(within(logDrawer).getAllByText('2026-06-13 17:11').length).toBeGreaterThanOrEqual(2);

    fireEvent.click(within(logDrawer).getByRole('button', { name: '取消任务' }));
    await waitFor(() =>
      expect(runnerTaskCancelBodies).toEqual([{ reason: '管理员从插件管理页面取消 Runner 任务' }]),
    );
    expect(await screen.findByText('Runner 任务已取消')).toBeInTheDocument();

    fireEvent.click(within(logDrawer).getByRole('button', { name: '重试任务' }));
    await waitFor(() =>
      expect(runnerTaskRetryBodies).toEqual([{ reason: '管理员从插件管理页面重试 Runner 任务' }]),
    );
    expect(await screen.findByText('Runner 任务已重新入队')).toBeInTheDocument();
    expect(within(logDrawer).getByText('ai_executor_task_retry_001')).toBeInTheDocument();
    expect(within(logDrawer).getByText(/Task retried from ai_executor_task_001/)).toBeInTheDocument();
  });

  it('shows the official plugin marketplace and opens guided connection setup', async () => {
    const { connectionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '插件市场' }));

    expect(await screen.findByText('官方插件市场')).toBeInTheDocument();
    expect(screen.getByText('连接 GitHub API，读取仓库、PR 和代码扫描数据。')).toBeInTheDocument();
    expect(screen.getByText('安全告警同步')).toBeInTheDocument();
    expect(screen.getByText('GitHub 代码巡检')).toBeInTheDocument();
    expect(screen.getByText('仓库地址')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '配置市场插件 GitHub' }));

    const dialog = await findDialogByTitle('新增连接');
    expect(within(dialog).getByLabelText('名称')).toHaveValue('生产 GitHub 连接');
    expect(within(dialog).getByDisplayValue('https://api.github.com')).toBeInTheDocument();
    expect(within(dialog).getByText('GitHub (http)')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Token / 密钥引用')).toHaveValue('');
    expect(within(dialog).getByText(/本地联调可直接填 ghp_xxx/)).toBeInTheDocument();
    expect(within(dialog).getByLabelText('仓库地址')).toBeInTheDocument();
    expect(within(dialog).getByText(/只需要配置 Token/)).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('application/vnd.github+json')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    expect(await screen.findByText('请填写 GitHub Token 或密钥引用')).toBeInTheDocument();
    expect(connectionBodies).toEqual([]);

    fireEvent.change(within(dialog).getByLabelText('Token / 密钥引用'), {
      target: { value: 'ghp_test_token' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(connectionBodies).toEqual([
        expect.objectContaining({
          auth_config: { token_ref: 'ghp_test_token' },
          auth_type: 'bearer',
          plugin_id: 'plugin_standard_github',
          request_config: {
            headers: {
              Accept: 'application/vnd.github+json',
              'X-GitHub-Api-Version': '2022-11-28',
            },
          },
        }),
      ]),
    );
  });

  it('configures DingTalk MCP marketplace connections with URL key auth', async () => {
    const { connectionBodies } = installPluginsFetchMock({
      includeDingTalkPlugins: true,
      includeOfficialPlugins: true,
    });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '插件市场' }));
    expect(await screen.findByText('钉钉官方')).toBeInTheDocument();
    expect(screen.getAllByText('mcp_streamable_http').length).toBeGreaterThanOrEqual(1);

    fireEvent.click(screen.getByRole('button', { name: '配置市场插件 钉钉文档' }));

    const dialog = await findDialogByTitle('新增连接');
    expect(within(dialog).getByLabelText('名称')).toHaveValue('钉钉文档 MCP 连接');
    expect(within(dialog).getByLabelText('StreamableHttp URL')).toHaveValue('');
    expect(within(dialog).getByText('钉钉文档 (mcp_streamable_http)')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('URL Key / 密钥引用')).toHaveValue('');
    expect(within(dialog).getByLabelText('查询参数名')).toHaveValue('key');
    const urlKeyGrid = dialog.querySelector('.plugin-connection-url-key-grid');
    expect(urlKeyGrid).toBeTruthy();
    expect(urlKeyGrid).toContainElement(within(dialog).getByLabelText('查询参数名'));
    expect(urlKeyGrid).toContainElement(within(dialog).getByLabelText('URL Key / 密钥引用'));
    expect(within(dialog).getByLabelText('授权主体')).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText('StreamableHttp URL'), {
      target: {
        value: 'https://mcp-gw.dingtalk.com/server/doc-instance-123?key=dingtalk-url-key-secret',
      },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(connectionBodies).toEqual([
        expect.objectContaining({
          auth_config: {
            auth_subject_type: 'user',
            query_key: 'key',
          },
          auth_type: 'url_key',
          endpoint_url: 'https://mcp-gw.dingtalk.com/server/doc-instance-123?key=dingtalk-url-key-secret',
          plugin_id: 'plugin_standard_dingtalk_doc',
          request_config: {},
        }),
      ]),
    );
  });

  it('shows DingTalk authorization guide, governance, observability, and business scenarios', async () => {
    const { pluginObservabilityCalls } = installPluginsFetchMock({
      includeDingTalkPlugins: true,
      includeOfficialPlugins: true,
    });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '插件市场' }));
    expect((await screen.findAllByText('钉钉文档')).length).toBeGreaterThan(0);

    await waitFor(() =>
      expect(pluginObservabilityCalls).toEqual(['/api/system/plugin-observability?provider=dingtalk']),
    );

    fireEvent.click(screen.getByRole('button', { name: '展开 marketplace_dingtalk_doc' }));

    expect(await screen.findByText('授权配置向导')).toBeInTheDocument();
    expect(screen.getByText('个人授权')).toBeInTheDocument();
    expect(screen.getByText('系统授权')).toBeInTheDocument();
    expect(screen.getByText('应用授权')).toBeInTheDocument();
    expect(screen.getByText('StreamableHttp URL 获取方式')).toBeInTheDocument();
    expect(screen.getByText('vault/dingtalk/shared/url_key')).toBeInTheDocument();
    expect(screen.getByText('动态能力发现')).toBeInTheDocument();
    expect(screen.getByText('tools/list')).toBeInTheDocument();
    expect(screen.getByText('新增工具生成动作模板')).toBeInTheDocument();
    expect(screen.getByText('高风险动作治理')).toBeInTheDocument();
    expect(screen.getByText('敏感读审计')).toBeInTheDocument();
    expect(screen.getByText('通知防误发')).toBeInTheDocument();
    expect(screen.getByText('插件健康看板')).toBeInTheDocument();
    expect(screen.getByText('连接成功率 50%')).toBeInTheDocument();
    expect(screen.getByText('P95 延迟 360ms')).toBeInTheDocument();
    expect(screen.getByText('脱敏请求回放')).toBeInTheDocument();
    expect(screen.getByText('从钉钉文档/知识库导入知识')).toBeInTheDocument();
    expect(screen.getByText('巡检结果发钉钉机器人')).toBeInTheDocument();
    expect(screen.getByText('生成方案文档到钉钉文档')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '配置市场插件 钉钉文档' }));
    const dialog = await findDialogByTitle('新增连接');
    expect(within(dialog).getByText('授权配置向导')).toBeInTheDocument();
    expect(within(dialog).getByText('StreamableHttp URL 获取方式')).toBeInTheDocument();
    expect(within(dialog).getByText(/改用 vault\/dingtalk\/doc\/key/)).toBeInTheDocument();
  });

  it('discovers DingTalk MCP tools from the connection list and shows drift hints', async () => {
    const { connectionDiscoveryCalls } = installPluginsFetchMock({
      includeDingTalkPlugins: true,
      includeOfficialPlugins: true,
    });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));
    expect(await screen.findByText('钉钉文档个人授权')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '发现能力 钉钉文档个人授权' }));

    await waitFor(() =>
      expect(connectionDiscoveryCalls).toEqual([
        '/api/system/plugin-connections/connection_dingtalk_doc/discover-tools',
      ]),
    );
    const dialog = await findDialogByTitle('钉钉动态能力发现');
    expect(within(dialog).getByText('drift_detected')).toBeInTheDocument();
    expect(within(dialog).getByText('export_document')).toBeInTheDocument();
    expect(within(dialog).getByText('get_document_content')).toBeInTheDocument();
    expect(within(dialog).getByText('create_document')).toBeInTheDocument();
    expect(within(dialog).getByText('新增工具生成动作模板')).toBeInTheDocument();
    expect(within(dialog).getByText('key')).toBeInTheDocument();
    expect(within(dialog).getByText('***')).toBeInTheDocument();
  });

  it('configures DingTalk document update actions from scene templates', async () => {
    const { actionBodies } = installPluginsFetchMock({
      includeDingTalkPlugins: true,
      includeOfficialPlugins: true,
    });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await findDialogByTitle('新增动作');
    fireEvent.mouseDown(within(dialog).getByLabelText('配置场景'));
    const scenarioDropdown = document.querySelector<HTMLElement>(
      '.ant-select-dropdown:not(.ant-select-dropdown-hidden)',
    );
    expect(scenarioDropdown).toBeTruthy();
    fireEvent.click(within(scenarioDropdown!).getByText('钉钉文档 - 更新内容'));

    expect(within(dialog).queryByLabelText('插件')).not.toBeInTheDocument();
    expect(within(dialog).getByText('钉钉文档')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('钉钉文档链接或 ID')).toHaveValue('');
    expect(within(dialog).getByLabelText('写入内容')).toHaveValue('{{result_summary}}');
    expect(within(dialog).getByText('追加内容')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('返回文档 ID JSONPath')).toHaveValue('$.document_id');
    expect(within(dialog).getByLabelText('返回状态 JSONPath')).toHaveValue('$.status');

    fireEvent.change(within(dialog).getByLabelText('钉钉文档链接或 ID'), {
      target: {
        value: 'https://alidocs.dingtalk.com/i/nodes/b9Y4gmKWrekkKx2ET4dzY39d8GXn6lpz?doc_type=wiki_doc',
      },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          action_type: 'mcp_tool',
          code: 'update_dingtalk_document_content',
          connection_id: 'connection_dingtalk_doc',
          name: '钉钉文档 - 更新内容',
          plugin_id: 'plugin_standard_dingtalk_doc',
          request_config: expect.objectContaining({
            arguments: {
              format: 'markdown',
              markdown: '{{result_summary}}',
              mode: 'append',
              nodeId: 'b9Y4gmKWrekkKx2ET4dzY39d8GXn6lpz',
            },
            mcp: expect.objectContaining({ provider: 'dingtalk' }),
            tool_name: 'update_document',
          }),
          result_mapping: {
            content_template: '{{result_summary}}',
            document_id: 'b9Y4gmKWrekkKx2ET4dzY39d8GXn6lpz',
            document_id_path: '$.document_id',
            status_path: '$.status',
            write_mode: 'append',
            write_target: 'dingtalk_document',
          },
        }),
      ]),
    );
  });

  it('fills the DingTalk document update tool when the write target is selected directly', () => {
    expect(
      buildVisualRequestConfig({
        action_type: 'mcp_tool',
        content_template: '{{result_summary}}',
        document_id: 'https://alidocs.dingtalk.com/i/nodes/b9Y4gmKWrekkKx2ET4dzY39d8GXn6lpz?doc_type=wiki_doc',
        request_config: '{}',
        write_mode: 'append',
        write_target: 'dingtalk_document',
      }),
    ).toEqual({
      arguments: {
        format: 'markdown',
        markdown: '{{result_summary}}',
        mode: 'append',
        nodeId: 'b9Y4gmKWrekkKx2ET4dzY39d8GXn6lpz',
      },
      mcp: {
        provider: 'dingtalk',
        server_name: 'doc',
      },
      tool_name: 'update_document',
    });
  });

  it('shows template version status and copies an official plugin as custom', async () => {
    const { pluginCopyBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });

    render(<PluginsPage />);

    expect(await screen.findByText('GitHub')).toBeInTheDocument();
    expect(screen.getAllByText('v1 最新').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: '复制官方插件 GitHub' }));

    await waitFor(() =>
      expect(pluginCopyBodies).toEqual([
        {
          code: 'github_custom',
          name: 'GitHub 副本',
        },
      ]),
    );
    expect(await screen.findByText('官方插件已复制为自定义插件')).toBeInTheDocument();
  });

  it('opens official action templates from the plugin marketplace', async () => {
    const { actionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '插件市场' }));
    fireEvent.click(await screen.findByRole('button', { name: '从市场插件 GitHub 创建动作' }));

    const dialog = await findDialogByTitle('新增动作');
    expect(within(dialog).queryByLabelText('插件')).not.toBeInTheDocument();
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
    fireEvent.click(await screen.findByRole('button', { name: '从市场插件 GitHub 创建动作' }));

    expect(warningSpy).toHaveBeenCalledWith('动作模板目录未返回该官方插件模板，请刷新服务端模板目录后重试');
    expect(screen.queryByText('新增动作')).not.toBeInTheDocument();
    expect(actionBodies).toEqual([]);
  });

  it('applies assistant plugin action drafts to the action form and confirms through the server draft', async () => {
    const { actionBodies, assistantDraftConfirmIds, assistantDraftPatchBodies } = installPluginsFetchMock({
      includeOfficialPlugins: true,
    });
    window.sessionStorage.setItem(
      assistantScopedStorageKey(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY),
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
        title: 'GitHub 代码巡检动作',
      }),
    );

    render(<PluginsPage />);

    const dialog = await findDialogByTitle('新增动作');
    expect(
      window.sessionStorage.getItem(assistantScopedStorageKey(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY)),
    ).toBeNull();
    expect(within(dialog).queryByLabelText('插件')).not.toBeInTheDocument();
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
      expect(assistantDraftPatchBodies).toEqual([
        {
          modified_fields: [],
          payload: expect.objectContaining({
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
        },
      ]),
    );
    expect(assistantDraftConfirmIds).toEqual(['assistant_draft_github_plugin_action']);
    expect(actionBodies).toEqual([]);
  });

  it('applies assistant plugin connection drafts to the connection form and confirms through the server draft', async () => {
    const { assistantDraftConfirmIds, assistantDraftPatchBodies, connectionBodies } = installPluginsFetchMock({
      includeOfficialPlugins: true,
    });
    window.sessionStorage.setItem(
      assistantScopedStorageKey(ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY),
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
            query: {},
          },
          status: 'active',
          timeout_seconds: 30,
        },
        title: 'GitHub API 连接',
      }),
    );

    render(<PluginsPage />);

    const dialog = await findDialogByTitle('新增连接');
    expect(
      window.sessionStorage.getItem(assistantScopedStorageKey(ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY)),
    ).toBeNull();
    expect(within(dialog).getByText('GitHub (http)')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('名称')).toHaveValue('生产 GitHub 连接');
    expect(within(dialog).getByLabelText('Endpoint URL')).toHaveValue('https://api.github.com');
    await waitFor(() => expect(within(dialog).getByDisplayValue('vault/github/token')).toBeInTheDocument());
    expect(within(dialog).getByDisplayValue('Accept')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('application/vnd.github+json')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('X-GitHub-Api-Version')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('仓库地址')).toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText('仓库地址'), {
      target: { value: 'git@github.com:acme/ai-brain.git' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(assistantDraftPatchBodies).toEqual([
        {
          modified_fields: ['request_config'],
          payload: expect.objectContaining({
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
              query: { owner: 'acme', repo: 'ai-brain' },
            },
            status: 'active',
            timeout_seconds: 30,
          }),
        },
      ]),
    );
    expect(assistantDraftConfirmIds).toEqual(['assistant_draft_github_plugin_connection']);
    expect(connectionBodies).toEqual([]);
  });

  it('remembers assistant connection drafts and resolves dependent action drafts', async () => {
    const { actionBodies, assistantDraftConfirmIds, connectionBodies } = installPluginsFetchMock({
      includeOfficialPlugins: true,
    });
    window.sessionStorage.setItem(
      assistantScopedStorageKey(ASSISTANT_PLUGIN_CONNECTION_DRAFT_STORAGE_KEY),
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
    await waitFor(() => expect(within(connectionDialog).getByLabelText('仓库地址')).toBeInTheDocument());
    fireEvent.click(within(connectionDialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() => expect(assistantDraftConfirmIds).toEqual(['assistant_draft_github_plugin_connection']));
    expect(connectionBodies).toEqual([]);
    expect(
      JSON.parse(
        window.sessionStorage.getItem(
          assistantScopedStorageKey(ASSISTANT_DRAFT_RESOLUTION_STORAGE_KEY),
        ) ?? '{}',
      ),
    ).toEqual({
      assistant_draft_github_plugin_connection: {
        resource_id: 'connection_created',
        resource_type: 'plugin_connection',
        title: 'GitHub API 连接',
      },
    });

    cleanup();
    window.sessionStorage.setItem(
      assistantScopedStorageKey(ASSISTANT_PLUGIN_ACTION_DRAFT_STORAGE_KEY),
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
        title: 'GitHub 代码巡检动作',
      }),
    );

    render(<PluginsPage />);

    const actionDialog = await findDialogByTitle('新增动作');
    fireEvent.click(within(actionDialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(assistantDraftConfirmIds).toEqual([
        'assistant_draft_github_plugin_connection',
        'assistant_draft_github_plugin_action',
      ]),
    );
    expect(actionBodies).toEqual([]);
  });

  it('warns when deleting resources in use and can delete unused actions', async () => {
    const { actionDeleteIds, pluginDeleteIds } = installPluginsFetchMock();

    render(<PluginsPage />);

    expect(await screen.findByText('阿里云 MaxCompute')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '删除插件 阿里云 MaxCompute' }));
    expect(await screen.findByText('当前对象正在被使用，不能删除。请先解除下面的引用，或将其停用。')).toBeInTheDocument();
    expect(screen.getByText('连接：')).toBeInTheDocument();
    expect(screen.getByText('生产 MaxCompute 项目')).toBeInTheDocument();
    expect(screen.getByText('动作：')).toBeInTheDocument();
    expect(screen.getByText('调用反馈 API')).toBeInTheDocument();
    expect(pluginDeleteIds).toEqual([]);
    fireEvent.click(screen.getByRole('button', { name: /知道了|OK|确\s*定/ }));

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(await screen.findByRole('button', { name: '删除动作 调用反馈 API' }));
    await screen.findByText('确定删除动作「调用反馈 API」吗？');
    fireEvent.click(screen.getAllByRole('button', { name: /删\s*除/ }).at(-1)!);
    await waitFor(() => expect(actionDeleteIds).toEqual(['action_feedback_api']));
  });

  it('blocks deleting actions referenced by multi-resource scheduled jobs', async () => {
    const { actionDeleteIds } = installPluginsFetchMock({ includeMultiResourceScheduledJob: true });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(await screen.findByRole('button', { name: '删除动作 调用反馈 API' }));

    expect(await screen.findByText('当前对象正在被使用，不能删除。请先解除下面的引用，或将其停用。')).toBeInTheDocument();
    expect(screen.getByText('定时作业：')).toBeInTheDocument();
    expect(screen.getByText('多连接插件巡检')).toBeInTheDocument();
    expect(actionDeleteIds).toEqual([]);
  });

  it('keeps connection environment hidden and can test a connection', async () => {
    const { actionBodies, actionTrialBodies, connectionBodies, connectionTestCalls } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));
    expect(await screen.findByText('生产 MaxCompute 项目')).toBeInTheDocument();
    expect(screen.queryByText('全部环境')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /测试/ }));
    await waitFor(() =>
      expect(connectionTestCalls).toEqual(['/api/system/plugin-connections/connection_maxcompute_prod/test']),
    );
    expect(await screen.findByText('请求调试台')).toBeInTheDocument();
    expect(screen.getByText('请求回放台')).toBeInTheDocument();
    expect(screen.getByText('最近测试记录')).toBeInTheDocument();
    expect(screen.getByText('连接样例可复用')).toBeInTheDocument();
    expect(screen.getByText('进度：2/4 步已就绪')).toBeInTheDocument();
    expect(screen.getByText('当前：连接测试样例')).toBeInTheDocument();
    expect(screen.getByText('下一步：复制动作模板并试运行')).toBeInTheDocument();
    expect(screen.getByText('最终请求 · ready')).toBeInTheDocument();
    expect(screen.getByText('响应样例 · ready')).toBeInTheDocument();
    expect(screen.getByText('动作模板草案 · ready')).toBeInTheDocument();
    expect(screen.getByText('复制动作模板并自动使用连接测试响应样例试运行，生成写入预览。')).toBeInTheDocument();
    expect(screen.getByText('动作写入预览 · ready')).toBeInTheDocument();
    expect(screen.getByText('变量解析前 / 后差异')).toBeInTheDocument();
    expect(screen.getAllByText('解析前').length).toBeGreaterThan(0);
    expect(screen.getAllByText('解析后').length).toBeGreaterThan(0);
    expect(screen.getByRole('button', { name: '复制并试运行' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '复制为动作模板' })).toBeInTheDocument();
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
    expect(within(resolvedTestDialog).getByText('历史动作模板草案')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '复制并试运行' }));
    const actionDialogFromReplay = await findDialogByTitle('新增动作');
    expect(within(actionDialogFromReplay).getByLabelText('名称')).toHaveValue('生产 MaxCompute 项目 请求动作');
    expect(within(actionDialogFromReplay).getByLabelText('编码')).toHaveValue('test_connection_maxcompute_prod');
    expect(within(actionDialogFromReplay).queryByLabelText('插件')).not.toBeInTheDocument();
    expect(within(actionDialogFromReplay).getByText('生产 MaxCompute 项目')).toBeInTheDocument();
    fireEvent.click(within(actionDialogFromReplay).getByRole('button', { name: /OK|确\s*定/ }));
    await waitFor(() =>
      expect(actionBodies.at(-1)).toEqual(
        expect.objectContaining({
          code: 'test_connection_maxcompute_prod',
          connection_id: 'connection_maxcompute_prod',
          name: '生产 MaxCompute 项目 请求动作',
        }),
      ),
    );
    const trialDialogFromConnectionSample = await findDialogByTitle('动作试运行：生产 MaxCompute 项目 请求动作');
    expect(within(trialDialogFromConnectionSample).getByText('使用连接测试响应样例')).toBeInTheDocument();
    await waitFor(() =>
      expect(actionTrialBodies.at(-1)).toEqual({
        connection_id: 'connection_maxcompute_prod',
        input_payload: {},
        sample_response_summary: { body_preview: '{"ok":true}', status_code: 200 },
      }),
    );
    expect(await within(trialDialogFromConnectionSample).findByText('可复用到定时作业 dry-run')).toBeInTheDocument();
    expect(within(trialDialogFromConnectionSample).getByText('进度：4/4 步已就绪')).toBeInTheDocument();
    expect(within(trialDialogFromConnectionSample).getByText('当前：动作写入预览')).toBeInTheDocument();
    expect(within(trialDialogFromConnectionSample).getByText('下一步：生成定时作业草稿')).toBeInTheDocument();
    expect(within(trialDialogFromConnectionSample).getByText('连接输入映射 · ready')).toBeInTheDocument();
    expect(within(trialDialogFromConnectionSample).getByText('结果映射 · ready')).toBeInTheDocument();
    expect(within(trialDialogFromConnectionSample).getByText('全链路试运行 · ready')).toBeInTheDocument();
    fireEvent.click(within(trialDialogFromConnectionSample).getByRole('button', { name: /Cancel|取\s*消/ }));

    fireEvent.click(screen.getByRole('button', { name: '新增连接' }));
    const dialog = await findDialogByTitle('新增连接');
    expect(within(dialog).queryByLabelText('环境')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('认证配置 JSON')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('请求配置 JSON')).not.toBeInTheDocument();

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

  it('does not expose connection environment filtering in the connection list', async () => {
    const { connectionListCalls } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));
    expect(await screen.findByText('生产 MaxCompute 项目')).toBeInTheDocument();
    expect(screen.queryByText('全部环境')).not.toBeInTheDocument();
    expect(connectionListCalls.some((call) => call.includes('environment='))).toBe(false);
  });

  it('loads plugin connections and actions through server-side pagination', async () => {
    const { actionListCalls, connectionListCalls } = installPluginsFetchMock();

    render(<PluginsPage />);

    await waitFor(() =>
      expect(connectionListCalls).toContain(
        '/api/system/plugin-connections?page=1&page_size=10&sort_by=plugin_id&sort_order=asc',
      ),
    );
    expect(actionListCalls).toContain(
      '/api/system/plugin-actions?page=1&page_size=10&sort_by=plugin_id&sort_order=asc',
    );
  });

  it('renders plugin names in the connection list when the server provides plugin projection fields', async () => {
    installPluginsFetchMock({ includeProjectedPluginConnection: true });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));

    expect(await screen.findByText('用户反馈连接器')).toBeInTheDocument();
    expect(screen.getByText('通用 HTTP 插件')).toBeInTheDocument();
    expect(screen.queryByText('plugin_001')).not.toBeInTheDocument();
  });

  it('shows all available connections in the action selector even when the connection table is paged', async () => {
    const { connectionListCalls } = installPluginsFetchMock({ includeOutOfPageConnection: true });

    render(<PluginsPage />);

    await waitFor(() => {
      expect(connectionListCalls).toContain('/api/system/plugin-connections');
      expect(connectionListCalls).toContain(
        '/api/system/plugin-connections?page=1&page_size=10&sort_by=plugin_id&sort_order=asc',
      );
    });

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await findDialogByTitle('新增动作');
    fireEvent.mouseDown(within(dialog).getByLabelText('连接'));

    expect(await screen.findByText('AI 客服聊天记录连接')).toBeInTheDocument();
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

  it('can save and immediately test a plugin connection from the connection modal', async () => {
    const { connectionBodies, connectionTestCalls } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));
    fireEvent.click(await screen.findByRole('button', { name: '新增连接' }));
    const dialog = await findDialogByTitle('新增连接');

    fireEvent.change(getDialogField<HTMLInputElement>(dialog, 'name'), { target: { value: '临时 GitHub 连接' } });
    fireEvent.change(getDialogField<HTMLInputElement>(dialog, 'endpoint_url'), {
      target: { value: 'https://api.github.com' },
    });
    fireEvent.click(within(dialog).getByRole('button', { name: '保存并测试' }));

    await waitFor(() =>
      expect(connectionBodies).toEqual([
        expect.objectContaining({
          endpoint_url: 'https://api.github.com',
          name: '临时 GitHub 连接',
        }),
      ]),
    );
    await waitFor(() =>
      expect(connectionTestCalls).toContain('/api/system/plugin-connections/connection_created/test'),
    );
    expect((await screen.findAllByText('连接测试诊断')).length).toBeGreaterThan(0);
    expect(await screen.findByText('请求调试台')).toBeInTheDocument();
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

  it('locks official plugins while providing GitLab GitHub email and internal data source connection defaults', async () => {
    const { connectionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });

    render(<PluginsPage />);

    expect(await screen.findByText('GitLab')).toBeInTheDocument();
    expect(screen.getByText('GitHub')).toBeInTheDocument();
    expect(screen.getByText('邮箱')).toBeInTheDocument();
    expect(screen.getByText('内部数据源')).toBeInTheDocument();
    expect(screen.getAllByText('官方标准').length).toBeGreaterThanOrEqual(4);
    expect(screen.queryByRole('button', { name: '编辑插件 GitLab' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '删除插件 GitLab' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '编辑插件 GitHub' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '删除插件 GitHub' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '编辑插件 邮箱' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '删除插件 邮箱' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '编辑插件 内部数据源' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '删除插件 内部数据源' })).not.toBeInTheDocument();

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));
    fireEvent.click(screen.getByRole('button', { name: '新增连接' }));
    let dialog = await findDialogByTitle('新增连接');
    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('GitLab (http)'));

    expect(within(dialog).getByLabelText('Endpoint URL')).toHaveValue('http://gitlab.local');
    expect(await within(dialog).findByLabelText('Header 名')).toHaveValue('PRIVATE-TOKEN');
    expect(within(dialog).getByLabelText('Header 值/密钥引用')).toHaveValue('');
    expect(within(dialog).getByLabelText('GitLab 地址')).toBeInTheDocument();
    expect(within(dialog).getByText(/只需要配置 Endpoint 和 Token/)).toBeInTheDocument();
    expect(within(dialog).queryByLabelText('GitLab 项目 ID')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('API 版本')).not.toBeInTheDocument();
    expect(within(dialog).queryByDisplayValue('group_id')).not.toBeInTheDocument();

    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '生产 GitLab Token' } });
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
          endpoint_url: 'http://gitlab.local',
          name: '生产 GitLab Token',
          plugin_id: 'plugin_standard_gitlab',
          request_config: {},
        }),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增连接' }));
    dialog = await findDialogByTitle('新增连接');
    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('GitLab (http)'));
    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '生产 GitLab 项目默认' } });
    fireEvent.change(await within(dialog).findByLabelText('GitLab 地址'), {
      target: { value: 'http://gitlab.local/rd-platform/ai-brain.git' },
    });
    expect(within(dialog).getByLabelText('Endpoint URL')).toHaveValue('http://gitlab.local');
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
          endpoint_url: 'http://gitlab.local',
          name: '生产 GitLab 项目默认',
          plugin_id: 'plugin_standard_gitlab',
          request_config: {
            query: {
              api_version: 'v4',
              group_id: 'rd-platform',
              project_id: 'rd-platform%2Fai-brain',
              project_path: 'rd-platform/ai-brain',
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
    expect(await within(dialog).findByLabelText('Token / 密钥引用')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('Accept')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('application/vnd.github+json')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('X-GitHub-Api-Version')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('2022-11-28')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('仓库地址')).toBeInTheDocument();
    expect(within(dialog).queryByDisplayValue('owner')).not.toBeInTheDocument();
    expect(within(dialog).queryByDisplayValue('repo')).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('邮箱 (http)'));

    expect(within(dialog).getByLabelText('Endpoint URL')).toHaveValue('https://mail-gateway.example.com/api');
    expect(await within(dialog).findByLabelText('Header 名')).toHaveValue('Authorization');
    expect(within(dialog).getByDisplayValue('Content-Type')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('application/json')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('mail_provider')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('enterprise_mail_gateway')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('默认发件人')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('默认收件人')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('subject_template')).toBeInTheDocument();
    expect(within(dialog).getByDisplayValue('[AI Brain] {{job_name}} 执行结果')).toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('内部数据源 (internal_read_model)'));

    await waitFor(() =>
      expect(within(dialog).queryByLabelText('Endpoint URL')).not.toBeInTheDocument(),
    );
    expect(within(dialog).queryByLabelText('认证')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('高级查询 Params')).not.toBeInTheDocument();
    expect(within(dialog).queryByText('Headers')).not.toBeInTheDocument();
    expect(within(dialog).getByText('内部数据源用于读取 AI Brain 内部业务数据。')).toBeInTheDocument();
    expect(
      within(dialog).getByText(/常用按源过滤可直接在下方表单选择/),
    ).toBeInTheDocument();
    expect(within(dialog).getByText('用户洞察数据')).toBeInTheDocument();
    expect(within(dialog).getByText('需求数据')).toBeInTheDocument();
    expect(within(dialog).getByText('产品数据')).toBeInTheDocument();
    expect(within(dialog).getByText('Bug 数据')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('需求状态')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('需求优先级')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Bug 状态')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('Bug 严重级别')).toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('需求状态'));
    fireEvent.click(await screen.findByText('已排期'));
    fireEvent.mouseDown(within(dialog).getByLabelText('需求优先级'));
    fireEvent.click((await screen.findAllByText('P0')).at(-1)!);
    fireEvent.mouseDown(within(dialog).getByLabelText('Bug 状态'));
    fireEvent.click(await screen.findByText('待处理'));
    fireEvent.mouseDown(within(dialog).getByLabelText('Bug 严重级别'));
    fireEvent.click((await screen.findAllByText('critical')).at(-1)!);

    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '内部数据源连接' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(connectionBodies.at(-1)).toEqual(
        expect.objectContaining({
          auth_config: {},
          auth_type: 'none',
          endpoint_url: 'internal://e-ai-brain/business-data',
          name: '内部数据源连接',
          plugin_id: 'plugin_standard_internal_data_source',
          request_config: {
	            query: {
	              field_mode: 'summary',
	              limit: 100,
	              source_filters: {
                bugs: {
                  severity: 'critical',
                  status: 'open',
                },
                requirements: {
                  priority: 'P0',
                  status: 'planned',
                },
              },
              source_types: ['user_insights', 'requirements', 'products', 'bugs'],
              window_end: '{{now}}',
              window_start: '{{current_date-30}}',
            },
          },
        }),
      ),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增连接' }));
    const filteredDialog = await findDialogByTitle('新增连接');
    fireEvent.mouseDown(within(filteredDialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('内部数据源 (internal_read_model)'));

    await waitFor(() =>
      expect(within(filteredDialog).getByLabelText('Bug 状态')).toBeInTheDocument(),
    );
    fireEvent.mouseDown(within(filteredDialog).getByLabelText('Bug 状态'));
    fireEvent.click(await screen.findByText('待处理'));
    fireEvent.mouseDown(within(filteredDialog).getByLabelText('需求优先级'));
    fireEvent.click((await screen.findAllByText('P0')).at(-1)!);

    removeSelectedTag(filteredDialog, '需求数据');
    removeSelectedTag(filteredDialog, 'Bug 数据');

    await waitFor(() =>
      expect(within(filteredDialog).queryByLabelText('需求优先级')).not.toBeInTheDocument(),
    );
    expect(within(filteredDialog).queryByLabelText('Bug 状态')).not.toBeInTheDocument();
    expect(within(filteredDialog).queryByText('按源过滤')).not.toBeInTheDocument();

    fireEvent.change(within(filteredDialog).getByLabelText('名称'), {
      target: { value: '内部产品洞察连接' },
    });
    fireEvent.click(within(filteredDialog).getByRole('button', { name: /OK|确\s*定/ }));

    await waitFor(() =>
      expect(connectionBodies.at(-1)).toEqual(
        expect.objectContaining({
          name: '内部产品洞察连接',
          request_config: {
            query: expect.objectContaining({
              source_types: ['user_insights', 'products'],
            }),
          },
        }),
      ),
    );
    const latestConnectionBody = connectionBodies.at(-1) as
      | { request_config?: { query?: Record<string, unknown> } }
      | undefined;
    expect(latestConnectionBody?.request_config?.query).not.toHaveProperty('source_filters');
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

    const actionsTab = screen.getByRole('tab', { name: '动作' });
    fireEvent.click(actionsTab);
    await waitFor(() => expect(actionsTab).toHaveAttribute('aria-selected', 'true'));
    fireEvent.click(await screen.findByRole('button', { name: '编辑动作 调用反馈 API' }));
    const dialog = await findDialogByTitle('编辑动作');
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

  it('prefills the scene template when editing official plugin actions', async () => {
    installPluginsFetchMock({ includeOfficialActions: true, includeOfficialPlugins: true });

    render(<PluginsPage />);

    const actionsTab = screen.getByRole('tab', { name: '动作' });
    fireEvent.click(actionsTab);
    await waitFor(() => expect(actionsTab).toHaveAttribute('aria-selected', 'true'));
    fireEvent.click(await screen.findByRole('button', { name: '编辑动作 GitHub 代码巡检' }));

    const dialog = await findDialogByTitle('编辑动作');

    expect(within(dialog).getByText('GitHub 代码巡检')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('请求路径')).toHaveValue('/repos/{{owner}}/{{repo}}/dependabot/alerts');
    expect(within(dialog).getByText('代码巡检报告')).toBeInTheDocument();
  });

  it('builds request config from visual params and headers by default', async () => {
    const { actionBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await findDialogByTitle('新增动作');
    expect(within(dialog).getByLabelText('结果写入目标')).toBeInTheDocument();
    expect(within(dialog).getByText('仅保存运行结果')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('导入数量 JSONPath')).toBeInTheDocument();
    expect(within(dialog).queryByLabelText('洞察列表 JSONPath')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('插件')).not.toBeInTheDocument();
    fireEvent.mouseDown(within(dialog).getByLabelText('连接'));
    fireEvent.click((await screen.findAllByText('生产 MaxCompute 项目')).at(-1)!);
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

  it('keeps user insight result mapping hidden while preserving default mapping', async () => {
    const { actionBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await findDialogByTitle('新增动作');
    expect(within(dialog).getByLabelText('导入数量 JSONPath')).toBeInTheDocument();
    expect(within(dialog).queryByLabelText('洞察列表 JSONPath')).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('结果写入目标'));
    fireEvent.click(await screen.findByText('用户洞察表'));

    expect(within(dialog).queryByLabelText('洞察列表 JSONPath')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('源表行数 JSONPath')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('原始行列表 JSONPath')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('导入数量 JSONPath')).not.toBeInTheDocument();

    expect(within(dialog).queryByLabelText('插件')).not.toBeInTheDocument();
    fireEvent.mouseDown(within(dialog).getByLabelText('连接'));
    fireEvent.click((await screen.findAllByText('生产 MaxCompute 项目')).at(-1)!);
    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '写入用户洞察' } });
    fireEvent.change(within(dialog).getByLabelText('编码'), { target: { value: 'write_user_insights' } });
    fireEvent.change(within(dialog).getByLabelText('请求路径'), { target: { value: '/insights/write' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          code: 'write_user_insights',
          result_mapping: {
            insights_path: '$.insights',
            records_imported_path: '$.row_count',
            rows_path: '$.rows',
            write_target: 'user_feedback_insights',
          },
        }),
      ]),
    );
  });

  it('offers code inspection reports as an action write target', async () => {
    const { actionBodies } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await findDialogByTitle('新增动作');
    fireEvent.mouseDown(within(dialog).getByLabelText('结果写入目标'));
    fireEvent.click(await screen.findByText('代码巡检报告'));

    expect(within(dialog).getByLabelText('Finding 列表 JSONPath')).toHaveValue('$.findings');
    expect(within(dialog).getByLabelText('仓库 ID JSONPath')).toHaveValue('$.repository_id');
    expect(within(dialog).getByLabelText('风险级别 JSONPath')).toHaveValue('$.risk_level');
    expect(within(dialog).queryByLabelText('洞察列表 JSONPath')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('导入数量 JSONPath')).not.toBeInTheDocument();

    expect(within(dialog).queryByLabelText('插件')).not.toBeInTheDocument();
    fireEvent.mouseDown(within(dialog).getByLabelText('连接'));
    fireEvent.click((await screen.findAllByText('生产 MaxCompute 项目')).at(-1)!);
    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '扫描仓库质量' } });
    fireEvent.change(within(dialog).getByLabelText('编码'), { target: { value: 'scan_repository_quality' } });
    fireEvent.change(within(dialog).getByLabelText('请求路径'), { target: { value: '/quality/scan' } });
    fireEvent.click(within(dialog).getByRole('button', { name: /确\s*定/ }));

    await waitFor(() =>
      expect(actionBodies).toEqual([
        expect.objectContaining({
          connection_id: 'connection_maxcompute_prod',
          code: 'scan_repository_quality',
          plugin_id: 'plugin_maxcompute',
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

  it('does not expose MaxCompute as an official action scene template', async () => {
    installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await findDialogByTitle('新增动作');
    fireEvent.mouseDown(within(dialog).getByLabelText('配置场景'));

    expect(await screen.findByText('GitHub 代码巡检')).toBeInTheDocument();
    expect(screen.queryByText('MaxCompute 每周用户反馈')).not.toBeInTheDocument();
  });

  it('creates official GitHub and GitLab code inspection actions from scene templates', async () => {
    const { actionBodies } = installPluginsFetchMock({ includeOfficialPlugins: true });

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await findDialogByTitle('新增动作');
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

    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));
    const nextDialog = await findDialogByTitle('新增动作');
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

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await findDialogByTitle('新增动作');
    fireEvent.mouseDown(within(dialog).getByLabelText('配置场景'));
    fireEvent.click(await screen.findByText('邮箱通知发送'));

    expect(within(dialog).queryByLabelText('插件')).not.toBeInTheDocument();
    expect(within(dialog).getByText('生产邮箱网关')).toBeInTheDocument();
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
    window.history.pushState({}, '', '/tasks/plugins');

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(await screen.findByText('试运行'));

    const dialog = await findDialogByTitle('动作试运行：调用反馈 API');
    expect(within(dialog).getByText('试运行输入通常无需填写')).toBeInTheDocument();
    expect(within(dialog).getByText(/默认使用动作里保存的请求配置试运行/)).toBeInTheDocument();
    expect(within(dialog).getByText('高级：临时覆盖输入 JSON')).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: '试运行' }));

    await waitFor(() =>
      expect(actionTrialBodies).toEqual([
        {
          connection_id: 'connection_maxcompute_prod',
          input_payload: {},
        },
      ]),
    );
    expect(await within(dialog).findByText('可复用到定时作业 dry-run')).toBeInTheDocument();
    expect(within(dialog).getByText('进度：4/4 步已就绪')).toBeInTheDocument();
    expect(within(dialog).getByText('下一步：生成定时作业草稿')).toBeInTheDocument();
    expect(within(dialog).getByText('写入预览 · ready')).toBeInTheDocument();
    expect(within(dialog).getByRole('link', { name: '生成作业草稿' })).toHaveAttribute(
      'href',
      '/tasks/scheduled-jobs?tab=jobs',
    );
    fireEvent.click(within(dialog).getByRole('link', { name: '生成作业草稿' }));
    const scheduledJobDraft = JSON.parse(
      window.sessionStorage.getItem(
        assistantScopedStorageKey(ASSISTANT_SCHEDULED_JOB_DRAFT_STORAGE_KEY),
      ) ?? '{}',
    );
    expect(scheduledJobDraft).toMatchObject({
      auto_dry_run: true,
      payload: {
        config_json: {
          sample_reuse: {
            auto_dry_run: true,
            connection_id: 'connection_maxcompute_prod',
            response_summary: {
              json: {
                commits: 8,
              },
            },
            sample_source: 'action_trial_response',
          },
        },
      },
    });
    expect(window.location.pathname).toBe('/tasks/scheduled-jobs');
    expect(window.location.search).toBe('?tab=jobs');
    expect(await within(dialog).findByText('写入预览')).toBeInTheDocument();
    expect(within(dialog).getByText('写入目标：定时作业结果')).toBeInTheDocument();
    expect(within(dialog).getByText('预计写入：8')).toBeInTheDocument();
    expect(within(dialog).getByText('候选记录：0')).toBeInTheDocument();
    expect(within(dialog).getByText('预览值')).toBeInTheDocument();
  });

  it('guides DingTalk document action trials without requiring JSON editing', async () => {
    const { actionTrialBodies } = installPluginsFetchMock({
      includeDingTalkPlugins: true,
      includeOfficialPlugins: true,
    });
    window.history.pushState({}, '', '/tasks/plugins');

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    const actionCell = await screen.findByText('钉钉文档 - 更新内容');
    const actionRow = actionCell.closest('tr');
    expect(actionRow).toBeTruthy();
    expect(within(actionRow!).getAllByText('钉钉文档')).toHaveLength(2);
    fireEvent.click(within(actionRow!).getByRole('button', { name: /试运行/ }));

    const dialog = await findDialogByTitle('动作试运行：钉钉文档 - 更新内容');
    expect(within(dialog).getByText('默认按动作配置试运行')).toBeInTheDocument();
    expect(within(dialog).getByText(/通常不用填写下面的 JSON/)).toBeInTheDocument();
    expect(within(dialog).getByText(/文档 ID：b9Y4gmKWrekkKx2ET4dzY39d8GXn6lpz/)).toBeInTheDocument();
    expect(within(dialog).getByText('写入方式：追加内容')).toBeInTheDocument();
    expect(within(dialog).getByText('写入内容：{{result_summary}}')).toBeInTheDocument();
    expect(within(dialog).getByText('高级：临时覆盖输入 JSON')).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: '试运行' }));

    await waitFor(() =>
      expect(actionTrialBodies.at(-1)).toEqual({
        connection_id: 'connection_dingtalk_doc',
        input_payload: {},
      }),
    );
  });

  it('shows runner approval request details when an action trial is blocked', async () => {
    const { actionTrialBodies, aiExecutorApprovalBodies } = installPluginsFetchMock({
      failActionTrialWithApproval: true,
    });
    window.history.pushState({}, '', '/tasks/plugins');

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(await screen.findByText('试运行'));

    const dialog = await findDialogByTitle('动作试运行：调用反馈 API');
    fireEvent.click(within(dialog).getByRole('button', { name: '试运行' }));

    await waitFor(() => expect(actionTrialBodies).toHaveLength(1));
    expect(await within(dialog).findByText('AI 执行器高风险操作审批')).toBeInTheDocument();
    expect(within(dialog).getByText('动作试运行未就绪')).toBeInTheDocument();
    expect(within(dialog).getByText('进度：1/4 步已就绪')).toBeInTheDocument();
    expect(within(dialog).getByText('当前：动作写入预览')).toBeInTheDocument();
    expect(within(dialog).getByText('下一步：修复动作试运行')).toBeInTheDocument();
    expect(within(dialog).getByText('缺失 动作试运行成功结果、动作试运行响应样例、写入预览')).toBeInTheDocument();
    expect(within(dialog).queryByText('缺失 action_trial_succeeded、action_trial_response、write_preview')).not.toBeInTheDocument();
    expect(within(dialog).queryByRole('link', { name: '生成作业草稿' })).not.toBeInTheDocument();
    expect(within(dialog).getByText('请求：ai_executor_approval_request_001')).toBeInTheDocument();
    expect(within(dialog).getByText('下一步：创建平台人工审批')).toBeInTheDocument();
    expect(within(dialog).getByText('Git 推送或合并')).toBeInTheDocument();
    expect(within(dialog).getByText(/审批需补齐：审批 ID、审批通过标记、审批时间/)).toBeInTheDocument();
    expect(within(dialog).getByText('审批模板 JSON')).toBeInTheDocument();
    expect(within(dialog).getByText(/runner_safety_v1/)).toBeInTheDocument();

    fireEvent.click(within(dialog).getByRole('button', { name: '审批并重新试运行' }));
    await waitFor(() =>
      expect(aiExecutorApprovalBodies).toEqual([
        {
          approval_request: expect.objectContaining({
            approval_request_id: 'ai_executor_approval_request_001',
            blocked_operations: ['git_push_or_merge'],
          }),
          reason: '插件动作试运行高风险操作审批',
        },
      ]),
    );
    await waitFor(() => expect(actionTrialBodies).toHaveLength(2));
    expect(await within(dialog).findByText('可复用到定时作业 dry-run')).toBeInTheDocument();
    expect(within(dialog).getByText('进度：4/4 步已就绪')).toBeInTheDocument();
    expect(within(dialog).getByRole('link', { name: '生成作业草稿' })).toBeInTheDocument();
  });
});
