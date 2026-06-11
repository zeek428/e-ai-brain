import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import PluginsPage from '../src/pages/Plugins';

function installPluginsFetchMock() {
  const actionBodies: unknown[] = [];
  const connectionBodies: unknown[] = [];
  const connectionTestCalls: string[] = [];
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    if (input === '/api/system/plugins' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          items: [
            {
              category: 'data_warehouse',
              code: 'aliyun_maxcompute',
              id: 'plugin_maxcompute',
              name: '阿里云 MaxCompute',
              protocol: 'mcp_http',
              risk_level: 'high',
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
              auth_type: 'api_key_header',
              endpoint_url: 'https://ai-brain-maxcompute-mcp.internal/mcp',
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
    if (input === '/api/system/plugin-connections' && init?.method === 'POST') {
      connectionBodies.push(JSON.parse(String(init.body)));
      return jsonResponse({ data: { id: 'connection_created', status: 'active' } });
    }
    if (input === '/api/system/plugin-connections/connection_maxcompute_prod/test' && init?.method === 'POST') {
      connectionTestCalls.push(String(input));
      return jsonResponse({
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
          request_summary: { method: 'POST', protocol: 'mcp_http' },
          status: 'succeeded',
        },
      });
    }
    if (input === '/api/system/plugin-actions' && init?.method === 'GET') {
      return jsonResponse({ data: { items: [], total: 0 } });
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
    throw new Error(`Unexpected fetch call: ${String(input)}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);
  return { actionBodies, connectionBodies, connectionTestCalls };
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

  it('uses predefined connection environments and can test a connection', async () => {
    const { connectionBodies, connectionTestCalls } = installPluginsFetchMock();

    render(<PluginsPage />);

    fireEvent.click(await screen.findByRole('tab', { name: '连接' }));
    expect(await screen.findByText('生产')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: /测试/ }));
    await waitFor(() =>
      expect(connectionTestCalls).toEqual(['/api/system/plugin-connections/connection_maxcompute_prod/test']),
    );

    fireEvent.click(screen.getByRole('button', { name: '新增连接' }));
    const dialog = await screen.findByRole('dialog', { name: '新增连接' });
    expect(within(dialog).queryByRole('textbox', { name: '环境' })).not.toBeInTheDocument();
    expect(within(dialog).queryByLabelText('认证配置 JSON')).not.toBeInTheDocument();
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
          result_mapping: {},
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
            insights_path: '$.insights',
            records_imported_path: '$.row_count',
            rows_path: '$.rows',
          },
        }),
      ]),
    );
  });
});
