import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { message, Modal, notification } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import DashboardPage from '../src/pages/Dashboard';
import DevopsPage from '../src/pages/Devops';
import InsightsPage from '../src/pages/Insights';

describe('Dashboard page', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    notification.destroy();
    cleanup();
    window.localStorage.clear();
    window.history.pushState({}, '', '/');
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('renders dashboard and operation pages without placeholder data', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      const path = String(input);
      if (input === '/api/dashboard/it-team') {
        return jsonResponse({
          data: {
            latest_tasks: [
              {
                id: 'task_dashboard',
                status: 'waiting_review',
                task_type: 'product_detail_design',
                title: '首页看板任务',
              },
            ],
            pending_reviews: [{ id: 'review_dashboard', stage: 'product_detail_design' }],
            recent_audit_events: [
              { event_type: 'ai_task.started', id: 'audit_dashboard' },
            ],
            recent_knowledge_documents: [{ id: 'knowledge_dashboard', title: '首页知识' }],
            bug_status_counts: [{ count: 2, status: 'open' }],
            gitlab_daily_summary: {
              average_quality_score: 88.5,
              changed_files: 12,
              commit_count: 9,
              merge_request_count: 2,
              metric_count: 1,
              risk_count: 1,
            },
            iteration_suggestion_status_counts: [{ count: 1, status: 'suggested' }],
            jenkins_release_status_counts: [{ count: 1, status: 'failed' }],
            latest_high_severity_bugs: [
              {
                id: 'bug_dashboard',
                severity: 'critical',
                status: 'open',
                title: '首页严重 Bug',
              },
            ],
            metadata: {
              dashboard_cache: {
                cache_enabled: true,
                cache_hit: false,
                duration_ms: 57,
                generated_at: '2026-06-09T10:14:34.058724+00:00',
              },
            },
            online_log_summary: {
              error_count: 4,
              error_rate: 0.02,
              max_p95_latency_ms: 318.5,
              max_p99_latency_ms: 640.25,
              metric_count: 1,
              request_count: 200,
            },
            requirement_status_counts: [
              { count: 1, status: 'submitted' },
              { count: 1, status: 'designing' },
            ],
            summary: {
              active_products: 1,
              ai_tasks: 3,
              audit_events: 8,
              bugs: 2,
              gitlab_commits: 9,
              high_severity_bugs: 1,
              iteration_suggestions: 1,
              jenkins_releases: 1,
              knowledge_deposits: 2,
              knowledge_documents: 4,
              online_errors: 4,
              open_bugs: 2,
              pending_reviews: 1,
              requirements: 5,
              usage_events: 120,
              user_feedback: 3,
            },
            task_status_counts: [{ count: 1, status: 'waiting_review' }],
            time_range: '7d',
            usage_metric_summary: {
              active_users: 42,
              conversion_count: 15,
              error_count: 2,
              event_count: 120,
              metric_count: 1,
            },
            user_feedback_status_counts: [{ count: 3, status: 'open' }],
          },
        });
      }
      if (path.startsWith('/api/devops/operational-metrics')) {
        return jsonResponse({
          data: {
            items: [
              {
                category: 'GitLab 指标',
                id: 'gitlab_metric_dashboard',
                name: '首页仓库指标',
                status: 'collected',
                updated_at: '2026-06-04T08:00:00Z',
                value: 9,
              },
            ],
            page: 1,
            page_size: 10,
            total: 1,
          },
        });
      }
      if (path.startsWith('/api/insights/items')) {
        return jsonResponse({
          data: {
            items: [
              {
                category: '使用趋势',
                id: 'usage_dashboard',
                status: 'active',
                summary: '首页使用趋势',
                updated_at: '2026-06-04T08:00:00Z',
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

    const { rerender } = render(<DashboardPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '欢迎' })).not.toBeInTheDocument();
    expect(screen.queryByText('欢迎使用 AI Brain')).not.toBeInTheDocument();
    expect(screen.queryByText('从左侧菜单进入任务中心、需求交付、产品资产和运营治理。')).not.toBeInTheDocument();
    expect(await screen.findByText('IT 团队看板')).toBeInTheDocument();
    expect(screen.getByText('生成时间：2026-06-09 10:14:34')).toBeInTheDocument();
    expect(screen.queryByText(/真实数据窗口/)).not.toBeInTheDocument();
    expect(screen.queryByText(/实时刷新/)).not.toBeInTheDocument();
    expect(screen.queryByText(/57ms/)).not.toBeInTheDocument();
    expect(screen.getByText('需求总数')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('首页看板任务')).toBeInTheDocument();
    expect(screen.getByText('首页知识')).toBeInTheDocument();
    expect(screen.getByText('ai_task.started')).toBeInTheDocument();
    expect(screen.getByText('开放 Bug')).toBeInTheDocument();
    expect(screen.getByText('严重 Bug')).toBeInTheDocument();
    expect(screen.getByText('GitLab 提交')).toBeInTheDocument();
    expect(screen.getByText('发布记录')).toBeInTheDocument();
    expect(screen.getByText('用户反馈')).toBeInTheDocument();
    expect(screen.getByText('使用事件')).toBeInTheDocument();
    expect(screen.getAllByText('迭代建议').length).toBeGreaterThan(0);
    expect(screen.getByText('首页严重 Bug')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Bug 明细/ })).toHaveAttribute(
      'href',
      '/delivery/bugs',
    );
    expect(screen.getByRole('link', { name: /日志明细/ })).toHaveAttribute(
      'href',
      '/governance/devops',
    );

    rerender(<DevopsPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '研发运营看板' })).not.toBeInTheDocument();
    expect(screen.queryByText('后续阶段')).not.toBeInTheDocument();
    expect(screen.queryByText('GitLab/Jenkins/线上日志真实运营采集属于后续增强。')).not.toBeInTheDocument();
    expect(screen.queryByText('待接入')).not.toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('运营治理');
    expect(screen.getByText('日志监控指标')).toBeInTheDocument();
    expect(screen.getByText('GitLab 指标')).toBeInTheDocument();
    await waitFor(() => {
      const paths = fetchMock.mock.calls.map(([path]) => String(path));
      expect(paths.some((path) => path.startsWith('/api/devops/operational-metrics'))).toBe(true);
      expect(paths).toEqual(expect.arrayContaining(['/api/products?active_only=true&page_size=100']));
    });

    rerender(<InsightsPage />);

    expect(screen.queryByRole('heading', { level: 1, name: '用户洞察/迭代规划' })).not.toBeInTheDocument();
    expect(screen.getAllByText('用户洞察').length).toBeGreaterThan(0);
    expect(screen.queryByText('后续阶段')).not.toBeInTheDocument();
    expect(screen.queryByText('当前预留入口，后续接入用户使用、反馈和 AI 迭代建议。')).not.toBeInTheDocument();
    expect(screen.queryByText('待接入')).not.toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: '面包屑' })).toHaveTextContent('运营治理');
    expect(screen.getByText('使用趋势')).toBeInTheDocument();
    await waitFor(() => {
      const paths = fetchMock.mock.calls.map(([path]) => String(path));
      expect(paths.some((path) => path.startsWith('/api/insights/items'))).toBe(true);
    });
  });

  it('reloads the dashboard with a selected product filter', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (input === '/api/products?active_only=true&page_size=100') {
        return jsonResponse({
          data: {
            items: [
              { code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' },
              { code: 'ops-platform', id: 'product_ops', name: '运营平台', status: 'active' },
            ],
            total: 2,
          },
        });
      }
      if (input === '/api/dashboard/it-team?product_id=product_api') {
        return jsonResponse({
          data: {
            latest_tasks: [
              {
                id: 'task_product_dashboard',
                status: 'waiting_review',
                task_type: 'technical_solution',
                title: '研发平台筛选任务',
              },
            ],
            pending_reviews: [],
            recent_audit_events: [],
            recent_knowledge_documents: [],
            requirement_status_counts: [{ count: 2, status: 'approved' }],
            summary: {
              active_products: 1,
              ai_tasks: 1,
              audit_events: 0,
              knowledge_deposits: 0,
              knowledge_documents: 0,
              pending_reviews: 0,
              requirements: 2,
            },
            task_status_counts: [{ count: 1, status: 'waiting_review' }],
            time_range: 'all',
          },
        });
      }
      if (input === '/api/dashboard/it-team?product_id=product_api&time_range=7d') {
        return jsonResponse({
          data: {
            latest_tasks: [
              {
                id: 'task_product_dashboard',
                status: 'waiting_review',
                task_type: 'technical_solution',
                title: '研发平台筛选任务',
              },
            ],
            pending_reviews: [],
            recent_audit_events: [],
            recent_knowledge_documents: [],
            requirement_status_counts: [{ count: 2, status: 'approved' }],
            summary: {
              active_products: 1,
              ai_tasks: 1,
              audit_events: 0,
              bugs: 1,
              gitlab_commits: 3,
              high_severity_bugs: 1,
              iteration_suggestions: 1,
              jenkins_releases: 1,
              knowledge_deposits: 0,
              knowledge_documents: 0,
              online_errors: 2,
              open_bugs: 1,
              pending_reviews: 0,
              requirements: 2,
              usage_events: 20,
              user_feedback: 1,
            },
            task_status_counts: [{ count: 1, status: 'waiting_review' }],
            time_range: '7d',
          },
        });
      }
      if (input === '/api/dashboard/it-team') {
        return jsonResponse({
          data: {
            latest_tasks: [],
            pending_reviews: [],
            recent_audit_events: [],
            recent_knowledge_documents: [],
            requirement_status_counts: [],
            summary: {
              active_products: 2,
              ai_tasks: 0,
              audit_events: 0,
              knowledge_deposits: 0,
              knowledge_documents: 0,
              pending_reviews: 0,
              requirements: 0,
            },
            task_status_counts: [],
            time_range: 'all',
          },
        });
      }
      return jsonResponse({ data: { items: [], total: 0 } });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    render(<DashboardPage />);

    expect(await screen.findByText('IT 团队看板')).toBeInTheDocument();
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain('/api/products?active_only=true&page_size=100'),
    );
    fireEvent.change(await screen.findByLabelText('产品筛选'), {
      target: { value: 'product_api' },
    });

    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
        '/api/dashboard/it-team?product_id=product_api',
      ),
    );
    fireEvent.change(screen.getByLabelText('时间范围'), {
      target: { value: '7d' },
    });
    await waitFor(() =>
      expect(fetchMock.mock.calls.map(([path]) => path)).toContain(
        '/api/dashboard/it-team?product_id=product_api&time_range=7d',
      ),
    );
    expect(await screen.findByText('研发平台筛选任务')).toBeInTheDocument();
    expect(screen.getAllByText('2')).not.toHaveLength(0);
    expect(screen.getByRole('link', { name: /日志明细/ })).toHaveAttribute(
      'href',
      '/governance/devops?product_id=product_api&time_range=7d',
    );
    expect(screen.getByRole('link', { name: /洞察明细/ })).toHaveAttribute(
      'href',
      '/governance/insights?product_id=product_api&time_range=7d',
    );
    expect(
      fetchMock.mock.calls
        .map(([path]) => String(path))
        .some((path) => path.includes('/versions?active_only=true')),
    ).toBe(false);
  });
});
