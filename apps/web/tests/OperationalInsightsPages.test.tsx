import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import DevopsPage from '../src/pages/Devops';
import InsightsPage from '../src/pages/Insights';

function fillDatePicker(label: string, value: string) {
  const input = screen.getByLabelText(label);
  fireEvent.change(input, { target: { value } });
  fireEvent.blur(input);
}

describe('operational insights pages', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('creates and triages real user feedback from the insights page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
    });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      if (path.startsWith('/api/products?active_only=true')) {
        return jsonResponse({
          data: {
            items: [{ code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' }],
            total: 1,
          },
        });
      }
      if (path.startsWith('/api/product-versions?active_only=true')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/insights/user-feedback' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            content: '新反馈内容',
            created_by: 'user_admin',
            id: 'feedback_created',
            product_id: 'product_api',
            status: 'open',
          },
        });
      }
      if (input === '/api/insights/user-feedback/feedback_existing' && init?.method === 'PATCH') {
        return jsonResponse({
          data: {
            content: '已有反馈内容',
            id: 'feedback_existing',
            product_id: 'product_api',
            status: 'triaged',
            triage_note: '已纳入优化池',
          },
        });
      }
      if (
        input === '/api/insights/user-feedback/feedback_existing/convert-requirement' &&
        init?.method === 'POST'
      ) {
        return jsonResponse({
          data: {
            feedback: {
              content: '已有反馈内容',
              id: 'feedback_existing',
              product_id: 'product_api',
              related_requirement_id: 'requirement_from_feedback',
              status: 'linked',
            },
            requirement: {
              id: 'requirement_from_feedback',
              product_id: 'product_api',
              source: 'user_feedback',
              title: '已有反馈内容',
            },
          },
        });
      }
      if (path.startsWith('/api/insights/items')) {
        return jsonResponse({
          data: {
            items: [
              {
                category: '用户反馈',
                created_by: 'user_admin',
                id: 'feedback_existing',
                product_id: 'product_api',
                status: 'open',
                summary: '已有反馈内容',
                updated_at: '2026-06-20T13:02:00+00:00',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<InsightsPage />);

    expect(await screen.findByText('已有反馈内容')).toBeInTheDocument();
    expect(screen.getByText('2026-06-20 21:02')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: '数据类型' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: '摘要' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: '操作' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '详情' }));
    expect(await screen.findByRole('dialog', { name: '用户洞察详情' })).toBeInTheDocument();
    expect(screen.getAllByText('已有反馈内容')).not.toHaveLength(0);
    expect(screen.getByText('产品 ID')).toBeInTheDocument();
    expect(screen.getByText('product_api')).toBeInTheDocument();
    fireEvent.click(screen.getAllByLabelText('Close')[0]);
    fireEvent.click(screen.getByRole('button', { name: '登记反馈' }));
    await waitFor(() => expect(screen.getAllByLabelText('所属产品')).toHaveLength(2));
    fireEvent.mouseDown(screen.getAllByLabelText('所属产品')[1]);
    await waitFor(() => expect(screen.getAllByRole('option', { name: '研发平台' })).toHaveLength(2));
    fireEvent.click(screen.getAllByRole('option', { name: '研发平台' })[1]);
    fireEvent.change(screen.getByLabelText('反馈内容'), { target: { value: '新反馈内容' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/insights/user-feedback',
        'POST',
        JSON.stringify({
          content: '新反馈内容',
          feedback_type: 'improvement',
          product_id: 'product_api',
          source_channel: 'in_app',
        }),
      ]),
    );

    const feedbackRow = screen
      .getAllByRole('row')
      .find((row) => row.textContent?.includes('已有反馈内容'));
    expect(feedbackRow).toBeDefined();
    expect(within(feedbackRow as HTMLElement).getByRole('button', { name: '转需求' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '登记使用指标' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '生成迭代建议' })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '处理反馈' }));
    fireEvent.mouseDown(screen.getByLabelText('处理状态'));
    fireEvent.click(await screen.findByRole('option', { name: '已分诊' }));
    fireEvent.change(screen.getByLabelText('处理备注'), { target: { value: '已纳入优化池' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/insights/user-feedback/feedback_existing',
        'PATCH',
        JSON.stringify({
          status: 'triaged',
          triage_note: '已纳入优化池',
        }),
      ]),
    );
  });

  it('filters user insights by selected product', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const path = String(input);
      if (path.startsWith('/api/products?active_only=true')) {
        return jsonResponse({
          data: {
            items: [{ code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' }],
            total: 1,
          },
        });
      }
      if (path.startsWith('/api/product-versions?active_only=true')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path.startsWith('/api/insights/items')) {
        return jsonResponse({
          data: {
            items: [],
            page: 1,
            page_size: 10,
            total: 0,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<InsightsPage />);

    await screen.findByLabelText('所属产品');
    fireEvent.change(screen.getByLabelText('所属产品'), { target: { value: 'product_api' } });
    fireEvent.click(screen.getByRole('button', { name: '查询' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([path]) => String(path).includes('product_id=product_api'))).toBe(true),
    );
  });

  it('sorts user insights by updated time across insight categories', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const path = String(input);
      if (path.startsWith('/api/products?active_only=true')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path.startsWith('/api/product-versions?active_only=true')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (path.startsWith('/api/insights/items')) {
        return jsonResponse({
          data: {
            items: [
              {
                category: '用户反馈',
                created_by: 'user_admin',
                id: 'feedback_new',
                product_id: 'product_api',
                status: 'open',
                summary: '最新反馈',
                updated_at: '2026-06-04T09:00:00Z',
              },
              {
                category: '迭代建议',
                created_by: 'user_admin',
                id: 'suggestion_mid',
                product_id: 'product_api',
                status: 'suggested',
                summary: '中间建议',
                updated_at: '2026-06-03T08:00:00Z',
              },
              {
                category: '使用趋势',
                created_by: 'user_admin',
                feature_code: 'old-usage',
                id: 'usage_old',
                product_id: 'product_api',
                status: 'active',
                summary: 'old-usage',
                updated_at: '2026-06-01T08:00:00Z',
              },
            ],
            page: 1,
            page_size: 10,
            total: 3,
          },
        });
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<InsightsPage />);

    await screen.findByText('最新反馈');
    const tableText = screen.getByRole('table').textContent ?? '';
    expect(tableText.indexOf('最新反馈')).toBeLessThan(tableText.indexOf('中间建议'));
    expect(tableText.indexOf('中间建议')).toBeLessThan(tableText.indexOf('old-usage'));
  });

  it('records real GitLab daily code metrics from the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/devops/gitlab/daily-code-metrics' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            commit_count: 7,
            id: 'gitlab_metric_created',
            metric_date: '2026-06-01',
            product_id: 'product_api',
            repository_id: 'repo_api',
            status: 'collected',
          },
        });
      }
      if (input === '/api/devops/gitlab/daily-code-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/devops/jenkins/releases') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ops/online-log-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (String(input).startsWith('/api/products?active_only=true')) {
        return jsonResponse({
          data: {
            items: [{ code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' }],
            total: 1,
          },
        });
      }
      if (String(input).startsWith('/api/product-versions?active_only=true')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/products/product_api/git-repositories?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                default_branch: 'main',
                git_provider: 'gitlab',
                id: 'repo_api',
                name: '研发平台 API',
                project_path: 'rd/platform-api',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    await screen.findByRole('button', { name: '登记 GitLab 指标' });
    fireEvent.click(screen.getByRole('button', { name: '登记 GitLab 指标' }));
    fireEvent.mouseDown(screen.getByLabelText('所属产品'));
    fireEvent.click(await screen.findByRole('option', { name: '研发平台' }));
    fireEvent.mouseDown(screen.getByLabelText('Git 仓库'));
    fireEvent.click(await screen.findByRole('option', { name: '研发平台 API (rd/platform-api)' }));
    fillDatePicker('指标日期', '2026-06-01');
    fireEvent.change(screen.getByLabelText('提交数'), { target: { value: '7' } });
    fireEvent.change(screen.getByLabelText('活跃作者数'), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText('MR 数'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('变更文件数'), { target: { value: '18' } });
    fireEvent.change(screen.getByLabelText('新增行数'), { target: { value: '320' } });
    fireEvent.change(screen.getByLabelText('删除行数'), { target: { value: '48' } });
    fireEvent.change(screen.getByLabelText('质量评分'), { target: { value: '88.5' } });
    fireEvent.change(screen.getByLabelText('风险数量'), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/devops/gitlab/daily-code-metrics',
        'POST',
        JSON.stringify({
          active_author_count: 4,
          additions: 320,
          changed_files: 18,
          commit_count: 7,
          deletions: 48,
          merge_request_count: 2,
          metric_date: '2026-06-01',
          product_id: 'product_api',
          quality_score: 88.5,
          repository_id: 'repo_api',
          risk_count: 1,
          source_channel: 'manual_import',
          status: 'collected',
        }),
      ]),
    );
  });

  it('records real Jenkins release records from the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/devops/jenkins/releases' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            build_id: 'build-20260601-17',
            id: 'jenkins_release_created',
            job_name: 'rd-platform-deploy',
            product_id: 'product_release',
            status: 'success',
            version_id: 'version_release',
          },
        });
      }
      if (input === '/api/devops/gitlab/daily-code-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/devops/jenkins/releases') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ops/online-log-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (String(input).startsWith('/api/products?active_only=true')) {
        return jsonResponse({
          data: {
            items: [{ code: 'release-platform', id: 'product_release', name: '发布平台', status: 'active' }],
            total: 1,
          },
        });
      }
      if (String(input).startsWith('/api/product-versions?active_only=true')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1.2.0',
                id: 'version_release',
                name: 'v1.2.0',
                product_id: 'product_release',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    await screen.findByRole('button', { name: '登记 Jenkins 发布' });
    fireEvent.click(screen.getByRole('button', { name: '登记 Jenkins 发布' }));
    fireEvent.change(screen.getByLabelText('Jenkins Job'), { target: { value: 'rd-platform-deploy' } });
    fireEvent.change(screen.getByLabelText('Build ID'), { target: { value: 'build-20260601-17' } });
    fireEvent.change(screen.getByLabelText('Build 编号'), { target: { value: '17' } });
    fireEvent.change(screen.getByLabelText('发布环境'), { target: { value: 'staging' } });
    fireEvent.change(screen.getByLabelText('触发人'), { target: { value: 'jenkins-admin' } });
    fireEvent.change(screen.getByLabelText('Commit SHA'), { target: { value: 'abc123def456' } });
    fireEvent.change(screen.getByLabelText('耗时秒数'), { target: { value: '480' } });
    fillDatePicker('开始时间', '2026-06-01T12:22:00Z');
    fillDatePicker('部署时间', '2026-06-01T12:30:00Z');
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/devops/jenkins/releases',
        'POST',
        JSON.stringify({
          build_id: 'build-20260601-17',
          build_number: 17,
          commit_sha: 'abc123def456',
          deployed_at: '2026-06-01T12:30:00Z',
          duration_seconds: 480,
          environment: 'staging',
          job_name: 'rd-platform-deploy',
          product_id: 'product_release',
          source_channel: 'manual_import',
          started_at: '2026-06-01T12:22:00Z',
          status: 'success',
          trigger_actor: 'jenkins-admin',
          version_id: 'version_release',
        }),
      ]),
    );
  });

  it('creates and starts deployment requests from the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      const path = String(input);
      if (path.startsWith('/api/devops/operational-metrics')) {
        return jsonResponse({
          data: {
            items: [
              {
                category: '运维部署',
                environment: 'prod',
                id: 'deployment_request_001',
                status: 'pending_ops',
                title: '生产部署',
                updated_at: '2026-06-01T12:00:00Z',
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      if (input === '/api/devops/deployments' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            environment: 'prod',
            id: 'deployment_request_created',
            product_id: 'product_deploy',
            requirement_ids: ['requirement_deploy'],
            status: 'pending_ops',
            title: '生产部署',
            version_id: 'version_deploy',
          },
        });
      }
      if (input === '/api/devops/deployments/deployment_request_001/start' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            environment: 'prod',
            id: 'deployment_request_001',
            product_id: 'product_deploy',
            requirement_ids: ['requirement_deploy'],
            runs: [{ id: 'deployment_run_001', status: 'running' }],
            status: 'deploying',
            title: '生产部署',
            version_id: 'version_deploy',
          },
        });
      }
      if (path.startsWith('/api/products?active_only=true')) {
        return jsonResponse({
          data: {
            items: [{ code: 'deploy-platform', id: 'product_deploy', name: '部署平台', status: 'active' }],
            total: 1,
          },
        });
      }
      if (path.startsWith('/api/product-versions?active_only=true')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'v1.0.0',
                id: 'version_deploy',
                name: 'v1.0.0',
                product_id: 'product_deploy',
                status: 'testing',
              },
            ],
            total: 1,
          },
        });
      }
      if (path.startsWith('/api/requirements?')) {
        return jsonResponse({
          data: {
            items: [
              {
                assignee: 'release-owner',
                created_at: '2026-06-01T11:00:00Z',
                id: 'requirement_deploy',
                priority: 'P1',
                product_id: 'product_deploy',
                status: 'ready_for_release',
                title: '部署需求',
                updated_at: '2026-06-01T11:30:00Z',
                version_id: 'version_deploy',
              },
            ],
            page: 1,
            page_size: 100,
            total: 1,
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    expect(await screen.findByText('生产部署')).toBeInTheDocument();
    expect(screen.getByText('待运维执行')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '发起部署' }));
    await screen.findByRole('dialog', { name: '发起运维部署' });
    await waitFor(() => expect(screen.getByLabelText('部署需求')).not.toBeDisabled());
    fireEvent.change(screen.getByLabelText('部署标题'), { target: { value: '生产部署' } });
    await waitFor(() => expect(screen.getByText(/requirement_deploy/)).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText('回滚方案'), { target: { value: '回滚到上一稳定版本' } });
    fireEvent.click(screen.getByRole('button', { name: '创建部署单' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/devops/deployments',
        'POST',
        JSON.stringify({
          environment: 'prod',
          requirement_ids: ['requirement_deploy'],
          risk_level: 'medium',
          rollback_plan: '回滚到上一稳定版本',
          product_id: 'product_deploy',
          title: '生产部署',
          version_id: 'version_deploy',
        }),
      ]),
    );

    fireEvent.click(screen.getByRole('button', { name: '启动' }));
    await screen.findByRole('dialog', { name: '启动部署' });
    fireEvent.click(screen.getByRole('button', { name: '确认部署操作' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/devops/deployments/deployment_request_001/start',
        'POST',
        JSON.stringify({ executor_type: 'manual' }),
      ]),
    );
  });

  it('records real online log metrics from the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      if (input === '/api/ops/online-log-metrics' && init?.method === 'POST') {
        return jsonResponse({
          data: {
            environment: 'prod',
            id: 'online_log_metric_created',
            product_id: 'product_ops',
            status: 'collected',
            window_start: '2026-06-01T00:00:00Z',
          },
        });
      }
      if (input === '/api/devops/gitlab/daily-code-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/devops/jenkins/releases') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (input === '/api/ops/online-log-metrics') {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      if (String(input).startsWith('/api/products?active_only=true')) {
        return jsonResponse({
          data: {
            items: [
              {
                code: 'ops-platform',
                id: 'product_ops',
                modules: [{ code: 'checkout', id: 'module_checkout', name: '结算模块', status: 'active' }],
                name: '线上运营平台',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (String(input).startsWith('/api/product-versions?active_only=true')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    await screen.findByRole('button', { name: '登记线上日志' });
    fireEvent.click(screen.getByRole('button', { name: '登记线上日志' }));
    fireEvent.change(screen.getByLabelText('模块编码'), { target: { value: 'checkout' } });
    fireEvent.change(screen.getByLabelText('运行环境'), { target: { value: 'prod' } });
    fillDatePicker('窗口开始', '2026-06-01T00:00:00Z');
    fillDatePicker('窗口结束', '2026-06-01T01:00:00Z');
    fireEvent.change(screen.getByLabelText('请求数'), { target: { value: '2400' } });
    fireEvent.change(screen.getByLabelText('错误数'), { target: { value: '12' } });
    fireEvent.change(screen.getByLabelText('P95 延迟毫秒'), { target: { value: '318.5' } });
    fireEvent.change(screen.getByLabelText('P99 延迟毫秒'), { target: { value: '640.25' } });
    fireEvent.change(screen.getByLabelText('核心事件数'), { target: { value: '240' } });
    fireEvent.change(screen.getByLabelText('Top Errors JSON'), {
      target: { value: '[{"count":7,"message":"PaymentTimeout"}]' },
    });
    fireEvent.change(screen.getByLabelText('异常摘要'), {
      target: { value: 'checkout error spike after release' },
    });
    fireEvent.click(screen.getByRole('button', { name: '保存' }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method, init?.body])).toContainEqual([
        '/api/ops/online-log-metrics',
        'POST',
        JSON.stringify({
          anomaly_summary: 'checkout error spike after release',
          core_event_count: 240,
          environment: 'prod',
          error_count: 12,
          module_code: 'checkout',
          p95_latency_ms: 318.5,
          p99_latency_ms: 640.25,
          product_id: 'product_ops',
          request_count: 2400,
          source_channel: 'manual_import',
          status: 'collected',
          top_errors: [{ count: 7, message: 'PaymentTimeout' }],
          window_end: '2026-06-01T01:00:00Z',
          window_start: '2026-06-01T00:00:00Z',
        }),
      ]),
    );
  });

  it('shows only log monitoring metrics on the DevOps page', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (String(input).startsWith('/api/devops/operational-metrics')) {
        return jsonResponse({ data: { items: [], page: 1, page_size: 10, total: 0 } });
      }
      if (String(input).startsWith('/api/products?active_only=true')) {
        return jsonResponse({ data: { items: [], total: 0 } });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DevopsPage />);

    await screen.findByText('日志监控');
    expect(screen.getByText('日志监控指标')).toBeInTheDocument();
    expect(screen.queryByText('采集运行记录')).not.toBeInTheDocument();
    expect(screen.queryByText('待归属数据队列')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '登记采集运行' })).not.toBeInTheDocument();
    await waitFor(() => {
      const paths = fetchMock.mock.calls.map(([path]) => String(path));
      expect(paths.some((path) => path.startsWith('/api/devops/operational-metrics'))).toBe(true);
      expect(paths).not.toContain('/api/collectors/runs');
      expect(paths).not.toContain('/api/attribution/pending-items');
    });
  });

});
