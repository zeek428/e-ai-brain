import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import CodeInspectionsPage from '../src/pages/CodeInspections';

function installCodeInspectionsFetchMock() {
  const report = {
    branch: 'main',
    commit_sha: 'abc1234',
    committer_count: 1,
    committer_summary: [
      {
        bug_count: 1,
        email: 'alice@example.com',
        finding_count: 1,
        name: 'Alice Chen',
        severe_finding_count: 1,
        username: 'alice',
      },
    ],
    created_at: '2026-06-12T09:00:00Z',
    created_bug_ids: ['bug_code_001'],
    finding_count: 1,
    id: 'code_inspection_report_001',
    notification_ids: ['code_inspection_notification_001'],
    plugin_action_id: 'plugin_action_github_scan',
    plugin_connection_id: 'plugin_connection_github_prod',
    plugin_invocation_log_id: 'plugin_invocation_log_001',
    product_id: 'product_ai_brain',
    repository_id: 'repo_ai_brain',
    repository_name: 'AI Brain',
    repository_path: 'example/ai-brain',
    risk_level: 'critical',
    scheduled_job_id: 'scheduled_job_code_inspection_weekly',
    scheduled_job_run_id: 'scheduled_job_run_001',
    severe_finding_count: 1,
    source_system: 'github-code-scanner',
    status: 'completed',
    summary: '发现 1 个 critical 安全问题。',
  };
  const jsonResponse = (body: unknown) =>
    new Response(JSON.stringify(body), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    });
  const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
    expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
    const url = String(input);
    if (url.startsWith('/api/governance/code-inspections?') && init?.method === 'GET') {
      return jsonResponse({ data: { items: [report], page: 1, page_size: 10, total: 1 } });
    }
    if (url.startsWith('/api/governance/code-inspections/dashboard') && init?.method === 'GET') {
      return jsonResponse({
        data: {
          branch_ranking: [
            {
              branch: 'main',
              finding_count: 1,
              report_count: 1,
              repository_id: 'repo_ai_brain',
              repository_name: 'AI Brain',
              severe_finding_count: 1,
            },
          ],
          category_distribution: [{ category: 'security', count: 1 }],
          committer_ranking: [
            {
              bug_count: 1,
              email: 'alice@example.com',
              finding_count: 1,
              name: 'Alice Chen',
              severe_finding_count: 1,
              username: 'alice',
            },
          ],
          repository_ranking: [
            {
              branch_count: 1,
              finding_count: 1,
              report_count: 1,
              repository_id: 'repo_ai_brain',
              repository_name: 'AI Brain',
              repository_path: 'example/ai-brain',
              risk_level: 'critical',
              severe_finding_count: 1,
            },
          ],
          risk_distribution: [{ count: 1, risk_level: 'critical' }],
          rule_distribution: [
            {
              category: 'security',
              finding_count: 1,
              rule_id: 'SEC001',
              severity: 'critical',
              severe_finding_count: 1,
            },
          ],
          severity_distribution: [{ count: 1, severity: 'critical' }],
          sla: {
            bug_coverage_rate: 1,
            covered_by_bug_count: 1,
            oldest_uncovered_at: null,
            severe_finding_count: 1,
            severe_threshold: 'high',
            status: 'healthy',
            uncovered_severe_finding_count: 0,
          },
          summary: {
            bug_created_count: 1,
            critical_finding_count: 1,
            failed_report_count: 0,
            finding_count: 1,
            high_finding_count: 0,
            repository_count: 1,
            report_count: 1,
            severe_finding_count: 1,
          },
          trend: [
            {
              bug_count: 1,
              date: '2026-06-12',
              finding_count: 1,
              report_count: 1,
              severe_finding_count: 1,
            },
          ],
        },
      });
    }
    if (input === '/api/governance/code-inspections/code_inspection_report_001' && init?.method === 'GET') {
      return jsonResponse({
        data: {
          findings: [
            {
              category: 'security',
              committer_email: 'alice@example.com',
              committer_name: 'Alice Chen',
              created_bug_id: 'bug_code_001',
              file_path: 'src/config.py',
              id: 'code_inspection_finding_001',
              line_number: 12,
              recommendation: '补充结构化仓库扫描数据，包括 repository_id、branch、commit_sha 和 findings，避免详情页因为长建议内容撑开表格布局。',
              report_id: report.id,
              rule_id: 'inspection.incomplete_source_data',
              severity: 'critical',
              title: '扫描输入数据不完整，无法进行文件级代码审计',
            },
          ],
          notifications: [
            {
              channel: 'email',
              id: 'code_inspection_notification_001',
              message: 'Code inspection completed.',
              report_id: report.id,
              status: 'recorded',
              target: 'quality@example.com',
            },
          ],
          report,
        },
      });
    }
    throw new Error(`Unexpected fetch call: ${String(input)}`);
  });
  window.localStorage.setItem('ai_brain_access_token', 'token-admin');
  vi.stubGlobal('fetch', fetchMock);
  return { fetchMock };
}

describe('CodeInspectionsPage', () => {
  afterEach(() => {
    Modal.destroyAll();
    message.destroy();
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('shows scheduled job and plugin source trace in the detail dialog', async () => {
    installCodeInspectionsFetchMock();

    render(<CodeInspectionsPage />);

    await screen.findByText('code_inspection_report_001');
    expect(screen.getByText('规则维度统计')).toBeInTheDocument();
    expect(screen.getByText('仓库风险排行')).toBeInTheDocument();
    expect(screen.getByText('提交人风险排行')).toBeInTheDocument();
    expect(screen.getByText('严重问题 SLA')).toBeInTheDocument();
    expect(screen.getAllByText('SEC001').length).toBeGreaterThan(0);
    expect(screen.getAllByText('100%').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: '详情' }));

    const dialog = await screen.findByRole('dialog', { name: '代码巡检详情' });
    await waitFor(() => expect(within(dialog).getByText('来源链路')).toBeInTheDocument());

    expect(within(dialog).getByText('来源系统')).toBeInTheDocument();
    expect(within(dialog).getByText('github-code-scanner')).toBeInTheDocument();
    expect(within(dialog).getByText('来源作业')).toBeInTheDocument();
    expect(within(dialog).getByRole('link', { name: 'scheduled_job_code_inspection_weekly' })).toHaveAttribute(
      'href',
      '/tasks/scheduled-jobs?tab=jobs&job_id=scheduled_job_code_inspection_weekly',
    );
    expect(within(dialog).getByText('来源运行')).toBeInTheDocument();
    expect(within(dialog).getByRole('link', { name: 'scheduled_job_run_001' })).toHaveAttribute(
      'href',
      '/tasks/scheduled-jobs?tab=runs&run_id=scheduled_job_run_001',
    );
    expect(within(dialog).getByText('数据连接')).toBeInTheDocument();
    expect(within(dialog).getByText('plugin_connection_github_prod')).toBeInTheDocument();
    expect(within(dialog).getByText('结果动作')).toBeInTheDocument();
    expect(within(dialog).getByText('plugin_action_github_scan')).toBeInTheDocument();
    expect(within(dialog).getByText('插件调用')).toBeInTheDocument();
    expect(within(dialog).getByText('plugin_invocation_log_001')).toBeInTheDocument();
  });

  it('keeps long finding text readable in the detail dialog', async () => {
    installCodeInspectionsFetchMock();

    render(<CodeInspectionsPage />);

    await screen.findByText('code_inspection_report_001');
    fireEvent.click(screen.getByRole('button', { name: '详情' }));

    const dialog = await screen.findByRole('dialog', { name: '代码巡检详情' });
    const findingTitle = await within(dialog).findByText('扫描输入数据不完整，无法进行文件级代码审计');
    const findingsTable = findingTitle.closest('table');

    expect(findingsTable).toHaveStyle({ tableLayout: 'fixed' });
    expect(within(dialog).getAllByText('问题 / 建议').length).toBeGreaterThan(0);
    expect(findingTitle).toHaveStyle({
      wordBreak: 'break-word',
      whiteSpace: 'normal',
    });
    expect(within(dialog).getByText('inspection.incomplete_source_data')).toHaveStyle({
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    });
  });
});
