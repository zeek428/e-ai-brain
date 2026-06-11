import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import PluginsPage from '../src/pages/Plugins';

function createDeferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((nextResolve) => {
    resolve = nextResolve;
  });
  return { promise, resolve };
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
      request_summary: {
        header_sources: { Authorization: 'auth_config.api_key_header' },
        headers: { Authorization: 'APPCODE 208b5b1456ee445ca47a42c' },
        masked_placeholder_headers: [],
        method: 'POST',
        protocol: 'mcp_http',
        query: { start_pt: '20260604' },
        url: 'https://ai-brain-maxcompute-mcp.internal/mcp?start_pt=20260604',
      },
      response_summary: { body_preview: '{"ok":true}', status_code: 200 },
      status: 'succeeded',
    },
  };
}

function installPluginsFetchMock(options: { deferConnectionTest?: boolean; includeOfficialPlugins?: boolean } = {}) {
  const actionBodies: unknown[] = [];
  const actionDeleteIds: string[] = [];
  const actionUpdateBodies: unknown[] = [];
  const connectionBodies: unknown[] = [];
  const connectionDeleteIds: string[] = [];
  const connectionUpdateBodies: unknown[] = [];
  const connectionTestCalls: string[] = [];
  const pluginDeleteIds: string[] = [];
  const pluginUpdateBodies: unknown[] = [];
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
    if (input === '/api/system/plugins/plugin_maxcompute' && init?.method === 'PATCH') {
      pluginUpdateBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'plugin_maxcompute', status: 'active' } });
    }
    if (input === '/api/system/plugins/plugin_maxcompute' && init?.method === 'DELETE') {
      pluginDeleteIds.push('plugin_maxcompute');
      return jsonResponse({ data: { deleted: true, id: 'plugin_maxcompute' } });
    }
    if (input === '/api/system/plugin-connections' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              auth_type: 'api_key_header',
              endpoint_url: 'https://ai-brain-maxcompute-mcp.internal/mcp',
              environment: 'prod',
              id: 'connection_maxcompute_prod',
              name: '生产 MaxCompute 项目',
              plugin_id: 'plugin_maxcompute',
              request_config: {
                headers: { 'X-Workspace': 'prod' },
                query: { appCode: '208b5b1456ee445ca47a42c' },
              },
              status: 'active',
            },
          ],
          total: 1,
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
    throw new Error(`Unexpected fetch call: ${String(input)}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);
  return {
    actionBodies,
    actionDeleteIds,
    actionUpdateBodies,
    connectionBodies,
    connectionDeleteIds,
    connectionTestCalls,
    connectionUpdateBodies,
    pluginDeleteIds,
    pluginUpdateBodies,
    resolveConnectionTest: () => {
      connectionTestDeferred?.resolve(jsonResponse(pluginConnectionTestBody()));
    },
  };
}

describe('PluginsPage', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('uses predefined plugin categories instead of a free text field', async () => {
    installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('button', { name: '新增插件' }));

    const dialog = await screen.findByRole('dialog', { name: '新增插件' });
    expect(within(dialog).queryByRole('textbox', { name: '分类' })).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('分类'));
    expect((await screen.findAllByText('数据仓库 / BI')).length).toBeGreaterThan(0);
    expect(screen.getByText('DevOps / 代码平台')).toBeInTheDocument();
    expect(screen.getByText('日志 / 监控')).toBeInTheDocument();
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
    expect(screen.getByText('最终请求 URL')).toBeInTheDocument();
    expect(screen.getByText('Header 来源')).toBeInTheDocument();
    expect(screen.getByText('Authorization')).toBeInTheDocument();
    expect(screen.getByText('auth_config.api_key_header')).toBeInTheDocument();
    expect(screen.getByText('远端响应信息')).toBeInTheDocument();
    expect(screen.getByText('完整请求 JSON')).toBeInTheDocument();
    expect(screen.getAllByText(/ai-brain-maxcompute-mcp\.internal\/mcp\?start_pt=20260604/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole('button', { name: /OK|确\s*定|知道了/ }));

    fireEvent.click(screen.getByRole('button', { name: '新增连接' }));
    const dialog = await screen.findByRole('dialog', { name: '新增连接' });
    expect(within(dialog).queryByRole('textbox', { name: '环境' })).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('认证配置 JSON')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('请求配置 JSON')).not.toBeInTheDocument();
    fireEvent.mouseDown(within(dialog).getByLabelText('环境'));
    expect(await screen.findByText('预发 / Staging')).toBeInTheDocument();
    expect(screen.getAllByText('生产').length).toBeGreaterThan(0);

    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('阿里云 MaxCompute (mcp_http)'));
    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '生产 MaxCompute API' } });
    fireEvent.change(within(dialog).getByLabelText('Endpoint URL'), {
      target: { value: 'https://example.aliyunapi.com' },
    });
    fireEvent.mouseDown(within(dialog).getByLabelText('认证'));
    fireEvent.click((await screen.findAllByText('api_key_header')).at(-1)!);
    const headerNameInput = await within(dialog).findByLabelText('Header 名');
    fireEvent.change(headerNameInput, { target: { value: 'Authorization' } });
    fireEvent.change(await within(dialog).findByLabelText('Header 值/密钥引用'), {
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
    const dialog = await screen.findByRole('dialog', { name: '编辑插件' });
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
    let dialog = await screen.findByRole('dialog', { name: '新增连接' });
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
    dialog = await screen.findByRole('dialog', { name: '新增连接' });
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

    expect(within(dialog).getByLabelText('Endpoint URL')).toHaveValue('https://mail-gateway.example.com/api/send');
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
    let dialog = await screen.findByRole('dialog', { name: '编辑连接' });
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
    const dialog = await screen.findByRole('dialog', { name: '编辑动作' });
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

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await screen.findByRole('dialog', { name: '新增动作' });
    expect(within(dialog).getByLabelText('结果写入目标')).toBeInTheDocument();
    expect(within(dialog).getByText('仅保存运行结果')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('导入数量 JSONPath')).toBeInTheDocument();
    expect(within(dialog).queryByLabelText('洞察列表 JSONPath')).not.toBeInTheDocument();
    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('阿里云 MaxCompute (mcp_http)'));
    fireEvent.change(within(dialog).getByLabelText('名称'), { target: { value: '调用反馈 API' } });
    fireEvent.change(within(dialog).getByLabelText('编码'), { target: { value: 'fetch_feedback_api' } });
    fireEvent.change(within(dialog).getByLabelText('请求路径'), { target: { value: '/zqf_api/feedback' } });

    fireEvent.click(within(dialog).getByRole('button', { name: /添加 Params/ }));
    fireEvent.change(within(dialog).getByPlaceholderText('参数名'), { target: { value: 'start_pt' } });
    fireEvent.mouseDown(within(dialog).getByText('系统变量'));
    fireEvent.click(await screen.findByText('当前日期 - 7 天'));

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

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await screen.findByRole('dialog', { name: '新增动作' });
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

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await screen.findByRole('dialog', { name: '新增动作' });
    fireEvent.mouseDown(within(dialog).getByLabelText('结果写入目标'));
    fireEvent.click(await screen.findByText('代码巡检报告'));

    expect(within(dialog).getByLabelText('Finding 列表 JSONPath')).toHaveValue('$.findings');
    expect(within(dialog).getByLabelText('仓库 ID JSONPath')).toHaveValue('$.repository_id');
    expect(within(dialog).getByLabelText('风险级别 JSONPath')).toHaveValue('$.risk_level');
    expect(within(dialog).queryByLabelText('洞察列表 JSONPath')).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('导入数量 JSONPath')).not.toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByLabelText('插件'));
    fireEvent.click(await screen.findByText('阿里云 MaxCompute (mcp_http)'));
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

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await screen.findByRole('dialog', { name: '新增动作' });
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

    fireEvent.click(await screen.findByRole('tab', { name: '动作' }));
    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));

    const dialog = await screen.findByRole('dialog', { name: '新增动作' });
    fireEvent.mouseDown(within(dialog).getByLabelText('配置场景'));
    fireEvent.click(await screen.findByText('GitHub 代码巡检'));

    expect(within(dialog).getByText('代码巡检报告')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('请求路径')).toHaveValue('/repos/{{owner}}/{{repo}}/code-scanning/alerts');
    expect(within(dialog).getByLabelText('Finding 列表 JSONPath')).toHaveValue('$.findings');
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
            query: expect.objectContaining({ state: 'open' }),
          }),
          result_mapping: expect.objectContaining({
            findings_path: '$.findings',
            write_target: 'code_inspection_reports',
          }),
        }),
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增动作' }));
    const nextDialog = await screen.findByRole('dialog', { name: '新增动作' });
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
});
