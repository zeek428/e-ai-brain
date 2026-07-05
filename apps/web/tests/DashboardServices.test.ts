import { afterEach, describe, expect, it, vi } from 'vitest';

import { fetchActiveProductOptions, fetchItTeamDashboard } from '../src/services/aiBrain';

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('dashboard service API mappings', () => {
  it('fetches the dashboard with product and time range query parameters', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      expect(input).toBe('/api/dashboard/it-team?product_id=product_api&time_range=7d');
      return jsonResponse({
        data: {
          bug_status_counts: [{ count: 1, status: 'open' }],
          gitlab_daily_summary: {
            average_quality_score: 91,
            changed_files: 5,
            commit_count: 3,
            merge_request_count: 1,
            metric_count: 1,
            risk_count: 0,
          },
          iteration_suggestion_status_counts: [{ count: 1, status: 'suggested' }],
          jenkins_release_status_counts: [{ count: 1, status: 'success' }],
          latest_high_severity_bugs: [
            {
              id: 'bug_api',
              severity: 'critical',
              status: 'open',
              title: 'API Dashboard Bug',
            },
          ],
          latest_tasks: [],
          online_log_summary: {
            error_count: 2,
            error_rate: 0.01,
            max_p95_latency_ms: 128,
            max_p99_latency_ms: 256,
            metric_count: 1,
            request_count: 200,
          },
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
          task_status_counts: [],
          time_range: '7d',
          trend: {
            grain: 'day',
            points: [
              {
                ai_tasks_created: 1,
                completed_tasks: 0,
                gitlab_commits: 3,
                period: '2026-06-03',
                requirements_created: 2,
              },
            ],
            series: [
              {
                category: 'delivery',
                key: 'requirements_created',
                label: '新增需求',
                unit: 'count',
              },
              {
                category: 'delivery',
                key: 'ai_tasks_created',
                label: '新增 AI 任务',
                unit: 'count',
              },
              {
                category: 'engineering',
                key: 'gitlab_commits',
                label: 'GitLab 提交',
                unit: 'count',
              },
            ],
            time_range: '7d',
            window_end: '2026-06-03',
            window_start: '2026-06-03',
          },
          usage_metric_summary: {
            active_users: 4,
            conversion_count: 2,
            error_count: 1,
            event_count: 20,
            metric_count: 1,
          },
          user_feedback_status_counts: [{ count: 1, status: 'open' }],
        },
      });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchItTeamDashboard({ productId: 'product_api', timeRange: '7d' })).resolves.toMatchObject({
      bugStatusCounts: [{ count: 1, status: 'open' }],
      gitlabDailySummary: expect.objectContaining({ commitCount: 3, metricCount: 1 }),
      latestHighSeverityBugs: [{ id: 'bug_api', severity: 'critical', status: 'open', title: 'API Dashboard Bug' }],
      onlineLogSummary: expect.objectContaining({ errorCount: 2, errorRate: 0.01 }),
      requirementStatusCounts: [{ count: 2, status: 'approved' }],
      summary: expect.objectContaining({ activeProducts: 1, openBugs: 1, requirements: 2 }),
      timeRange: '7d',
      trend: expect.objectContaining({
        grain: 'day',
        points: [
          expect.objectContaining({
            gitlab_commits: 3,
            period: '2026-06-03',
            requirements_created: 2,
          }),
        ],
        series: expect.arrayContaining([
          expect.objectContaining({ key: 'requirements_created', label: '新增需求' }),
        ]),
        windowStart: '2026-06-03',
      }),
    });
  });

  it('fetches active product filter options without loading versions', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      expect(input).toBe('/api/products?active_only=true&page_size=100');
      return jsonResponse({
        data: {
          items: [
            { code: 'rd-platform', id: 'product_api', name: '研发平台', status: 'active' },
          ],
          total: 1,
        },
      });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await expect(fetchActiveProductOptions()).resolves.toEqual([
      { code: 'rd-platform', id: 'product_api', name: '研发平台' },
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
