import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { message, Modal } from 'antd';
import { afterEach, describe, expect, it, vi } from 'vitest';

import './proComponentsMock';

import CodeInspectionsPage from '../src/pages/CodeInspections';

function installCodeInspectionsFetchMock() {
  const report = {
    artifact_ref: 'workdir://checkouts/scheduled_job_run_001__repo_ai_brain__main__abc1234',
    branch: 'main',
    checkout_path_retained: false,
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
    created_task_ids: ['task_code_fix_001'],
    finding_count: 1,
    id: 'code_inspection_report_001',
    incremental_file_count: 3,
    incremental_from_commit: 'base1234',
    is_full_scan: false,
    files_scanned: 12,
    lines_scanned: 300,
    notification_ids: ['code_inspection_notification_001'],
    plugin_action_id: 'plugin_action_github_scan',
    plugin_connection_id: 'plugin_connection_github_prod',
    plugin_invocation_log_id: 'plugin_invocation_log_001',
    product_id: 'product_ai_brain',
    repository_id: 'repo_ai_brain',
    repository_name: 'AI Brain',
    repository_path: 'example/ai-brain',
    remote_url_hash: 'f00dbeef1234',
    remote_url_summary: 'https://github.com/example/ai-brain.git#f00dbeef1234',
    previous_comparison: {
      finding_delta: -1,
      previous_finding_count: 2,
      previous_report_id: 'code_inspection_report_previous',
      previous_severe_finding_count: 2,
      severe_finding_delta: -1,
    },
    previous_report_id: 'code_inspection_report_previous',
    quality_gate: {
      counts: { critical: 1, high: 0, medium: 0, total: 1 },
      enabled: true,
      status: 'failed',
      violations: [{ actual: 1, limit: 0, metric: 'critical', severity: 'critical' }],
    },
    risk_level: 'critical',
    rules_loaded: ['secrets', 'internal_addresses'],
    rules_version: 'builtin-2026.06.16',
    scan_profile: {
      external_scanner_status: {
        configured: ['gitleaks'],
        executed: ['gitleaks'],
        failed: [],
        skipped: [],
      },
      scanner_engines: ['builtin', 'gitleaks'],
      severity_threshold: 'medium',
    },
    scan_finished_at: '2026-06-12T09:01:00Z',
    scan_mode: 'native_full_scan',
    scan_started_at: '2026-06-12T09:00:00Z',
    scanner_name: 'ai_brain_builtin_static',
    scanner_version: '2026.06.16',
    scheduled_job_id: 'scheduled_job_code_inspection_weekly',
    scheduled_job_run_id: 'scheduled_job_run_001',
    severe_finding_count: 1,
    source_system: 'github-code-scanner',
    status: 'completed',
    summary: '发现 1 个 critical 安全问题。',
    suppressed_finding_count: 2,
    suppression_summary: {
      accepted_risk: 1,
      baseline: 1,
      ignored: 0,
      severity_threshold: 0,
    },
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
          rule_governance: {
            latest_report_rules_version: 'builtin-2026.06.16',
            latest_report_scanner_version: '2026.06.16',
            mixed_rules_version: true,
            mixed_scanner_version: false,
            report_with_suppression_count: 1,
            rule_version_distribution: [
              { count: 1, rules_version: 'builtin-2026.06.16' },
              { count: 1, rules_version: 'builtin-2026.06.01' },
            ],
            scanner_version_distribution: [{ count: 1, scanner_version: '2026.06.16' }],
            suppressed_finding_count: 2,
            suppression_distribution: [
              { count: 1, reason: 'accepted_risk' },
              { count: 1, reason: 'baseline' },
            ],
          },
          quality_gate_violations: [
            {
              actual: 1,
              latest_report_id: 'code_inspection_report_001',
              latest_report_summary: '发现 1 个 critical 安全问题。',
              limit: 0,
              metric: 'critical',
              report_count: 1,
              severity: 'critical',
              violation_count: 1,
            },
          ],
          severity_distribution: [{ count: 1, severity: 'critical' }],
          sla: {
            bug_coverage_rate: 1,
            covered_by_bug_count: 1,
            covered_by_task_count: 1,
            oldest_uncovered_at: null,
            oldest_without_task_at: null,
            severe_finding_count: 1,
            severe_threshold: 'high',
            status: 'healthy',
            task_coverage_rate: 1,
            uncovered_severe_finding_count: 0,
            uncovered_task_finding_count: 0,
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
              quality_gate_failed_count: 1,
              quality_gate_passed_count: 0,
              quality_gate_skipped_count: 0,
              quality_gate_unknown_count: 0,
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
              created_task_id: 'task_code_fix_001',
              file_path: 'src/config.py',
              id: 'code_inspection_finding_001',
              line_number: 12,
              recommendation: '补充结构化仓库扫描数据，包括 repository_id、branch、commit_sha 和 findings，避免详情页因为长建议内容撑开表格布局。',
              report_id: report.id,
              rule_id: 'inspection.incomplete_source_data',
              severity: 'critical',
              suppression_status: 'none',
              title: '扫描输入数据不完整，无法进行文件级代码审计',
            },
          ],
          governance_summary: {
            accepted_risk_count: 1,
            action_items: [],
            active_severe_finding_count: 1,
            bug_coverage_rate: 1,
            covered_by_bug_count: 1,
            covered_by_task_count: 1,
            pending_suppression_count: 0,
            severe_threshold: 'high',
            status: 'healthy',
            suppressed_finding_count: 2,
            task_coverage_rate: 1,
            uncovered_bug_finding_count: 0,
            uncovered_task_finding_count: 0,
          },
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
          scan_summary: {
            committer_distribution: [
              {
                email: 'alice@example.com',
                finding_count: 1,
                name: 'Alice Chen',
                severe_finding_count: 1,
                username: 'alice',
              },
            ],
            coverage: {
              files_scanned: 12,
              lines_scanned: 300,
              suppressed_finding_count: 2,
            },
            file_distribution: [
              {
                file_path: 'src/config.py',
                finding_count: 1,
                severe_finding_count: 1,
              },
            ],
            previous_comparison: report.previous_comparison,
            quality_gate: report.quality_gate,
            rule_distribution: [
              {
                category: 'security',
                finding_count: 1,
                rule_id: 'inspection.incomplete_source_data',
                severity: 'critical',
                severe_finding_count: 1,
              },
            ],
            scan_profile: report.scan_profile,
            suppression_summary: report.suppression_summary,
          },
        },
      });
    }
    if (
      input ===
        '/api/governance/code-inspections/code_inspection_report_001/findings/code_inspection_finding_001/suppression-request' &&
      init?.method === 'POST'
    ) {
      return jsonResponse({
        data: {
          findings: [
            {
              category: 'security',
              committer_email: 'alice@example.com',
              committer_name: 'Alice Chen',
              created_bug_id: 'bug_code_001',
              created_task_id: 'task_code_fix_001',
              file_path: 'src/config.py',
              id: 'code_inspection_finding_001',
              line_number: 12,
              recommendation: '补充结构化仓库扫描数据。',
              report_id: report.id,
              rule_id: 'inspection.incomplete_source_data',
              severity: 'critical',
              suppression_reason: 'false_positive',
              suppression_status: 'pending',
              title: '扫描输入数据不完整，无法进行文件级代码审计',
            },
          ],
          governance_summary: {
            action_items: [{ code: 'review_pending_suppression', count: 1, label: '审批待处理的忽略申请' }],
            active_severe_finding_count: 1,
            bug_coverage_rate: 1,
            covered_by_bug_count: 1,
            covered_by_task_count: 1,
            pending_suppression_count: 1,
            status: 'pending_review',
            task_coverage_rate: 1,
            uncovered_bug_finding_count: 0,
            uncovered_task_finding_count: 0,
          },
          notifications: [],
          report,
          scan_summary: {},
        },
      });
    }
    if (
      input ===
        '/api/governance/code-inspections/code_inspection_report_001/findings/code_inspection_finding_001/suppression-review' &&
      init?.method === 'POST'
    ) {
      return jsonResponse({
        data: {
          findings: [
            {
              category: 'security',
              committer_email: 'alice@example.com',
              committer_name: 'Alice Chen',
              created_bug_id: 'bug_code_001',
              created_task_id: 'task_code_fix_001',
              file_path: 'src/config.py',
              id: 'code_inspection_finding_001',
              line_number: 12,
              recommendation: '补充结构化仓库扫描数据。',
              report_id: report.id,
              rule_id: 'inspection.incomplete_source_data',
              severity: 'critical',
              suppression_reason: 'false_positive',
              suppression_status: 'approved',
              title: '扫描输入数据不完整，无法进行文件级代码审计',
            },
          ],
          governance_summary: {
            active_severe_finding_count: 1,
            bug_coverage_rate: 1,
            covered_by_bug_count: 1,
            covered_by_task_count: 1,
            pending_suppression_count: 0,
            status: 'healthy',
            task_coverage_rate: 1,
            uncovered_bug_finding_count: 0,
            uncovered_task_finding_count: 0,
          },
          notifications: [],
          report: {
            ...report,
            suppressed_finding_count: 3,
            suppression_summary: {
              ...report.suppression_summary,
              false_positive: 1,
            },
          },
          scan_summary: {},
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
    window.history.pushState({}, '', '/');
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('shows scheduled job and plugin source trace in the detail dialog', async () => {
    installCodeInspectionsFetchMock();

    render(<CodeInspectionsPage />);

    await screen.findByText('code_inspection_report_001');
    expect(screen.getAllByText('2026-06-12 17:00').length).toBeGreaterThan(0);
    expect(screen.getByText('规则维度统计')).toBeInTheDocument();
    expect(screen.getByText('规则包与误报治理')).toBeInTheDocument();
    expect(screen.getByText('最近规则版本')).toBeInTheDocument();
    expect(screen.getByText('版本不一致')).toBeInTheDocument();
    expect(screen.getByText('已过滤问题')).toBeInTheDocument();
    expect(screen.getAllByText('过滤原因').length).toBeGreaterThan(0);
    expect(screen.getByText('accepted_risk')).toBeInTheDocument();
    expect(screen.getByText('仓库风险排行')).toBeInTheDocument();
    expect(screen.getByText('提交人风险排行')).toBeInTheDocument();
    expect(screen.getByText('质量门禁趋势')).toBeInTheDocument();
    expect(screen.getByText('门禁失败原因')).toBeInTheDocument();
    expect(screen.getByText('严重问题 SLA')).toBeInTheDocument();
    expect(screen.getByText('整改任务覆盖率')).toBeInTheDocument();
    expect(screen.getByText('已生成整改任务')).toBeInTheDocument();
    expect(screen.getAllByText('整体 healthy').length).toBeGreaterThan(0);
    expect(screen.getAllByText('SEC001').length).toBeGreaterThan(0);
    expect(screen.getAllByText('实际/阈值').length).toBeGreaterThan(0);
    expect(screen.getAllByText('1 / 0').length).toBeGreaterThan(0);
    expect(screen.getByText('2026-06-12')).toBeInTheDocument();
    expect(screen.getAllByText('100%').length).toBeGreaterThan(0);

    fireEvent.click(screen.getByRole('button', { name: '详情' }));

    const dialog = await screen.findByRole('dialog', { name: '代码巡检详情' });
    await waitFor(() => expect(within(dialog).getByText('来源链路')).toBeInTheDocument());

    expect(within(dialog).getByText('执行诊断')).toBeInTheDocument();
    expect(within(dialog).getByRole('link', { name: '巡检报告诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=code_inspection_report_001&source_type=code_inspection_report',
    );
    expect(within(dialog).getByRole('link', { name: '运行诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=scheduled_job_run_001&source_type=scheduled_job_run',
    );
    expect(within(dialog).getByRole('link', { name: '插件诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=plugin_invocation_log_001&source_type=plugin_invocation_log',
    );
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
    expect(within(dialog).getByRole('link', { name: 'plugin_invocation_log_001' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=plugin_invocation_log_001&source_type=plugin_invocation_log',
    );
    expect(within(dialog).getByText('扫描快照')).toBeInTheDocument();
    expect(within(dialog).getByText('扫描范围')).toBeInTheDocument();
    expect(within(dialog).getByText('增量扫描')).toBeInTheDocument();
    expect(within(dialog).getByText('native_full_scan')).toBeInTheDocument();
    expect(within(dialog).getByText('增量基线 Commit')).toBeInTheDocument();
    expect(within(dialog).getByText('base1234')).toBeInTheDocument();
    expect(within(dialog).getByText('增量文件数')).toBeInTheDocument();
    expect(within(dialog).getByText('3')).toBeInTheDocument();
    expect(within(dialog).getByText('workdir://checkouts/scheduled_job_run_001__repo_ai_brain__main__abc1234')).toBeInTheDocument();
    expect(within(dialog).getByText('builtin-2026.06.16')).toBeInTheDocument();
    expect(within(dialog).getByText('未保留')).toBeInTheDocument();
    expect(within(dialog).getByText('2026-06-12 17:00')).toBeInTheDocument();
    expect(within(dialog).getByText('2026-06-12 17:01')).toBeInTheDocument();
    expect(within(dialog).getByText('扫描摘要')).toBeInTheDocument();
    expect(within(dialog).getByText('质量门禁')).toBeInTheDocument();
    expect(within(dialog).getByText('failed')).toBeInTheDocument();
    expect(within(dialog).getByText('过滤问题数')).toBeInTheDocument();
    expect(within(dialog).getByText('2')).toBeInTheDocument();
    expect(within(dialog).getByText('扫描引擎')).toBeInTheDocument();
    expect(within(dialog).getByText('builtin、gitleaks')).toBeInTheDocument();
    expect(within(dialog).getByText('外部引擎状态')).toBeInTheDocument();
    expect(within(dialog).getByText('已执行 gitleaks')).toBeInTheDocument();
    expect(within(dialog).getByText('与上次对比')).toBeInTheDocument();
    expect(within(dialog).getByText('治理闭环')).toBeInTheDocument();
    expect(within(dialog).getByText('闭环状态')).toBeInTheDocument();
    expect(within(dialog).getByText('已闭环')).toBeInTheDocument();
    expect(within(dialog).getByText('有效严重问题')).toBeInTheDocument();
    expect(within(dialog).getByText('Bug 覆盖')).toBeInTheDocument();
    expect(within(dialog).getByText('整改任务覆盖')).toBeInTheDocument();
    expect(within(dialog).getByText('未关联 Bug')).toBeInTheDocument();
    expect(within(dialog).getByText('未派生任务')).toBeInTheDocument();
    expect(within(dialog).getByRole('link', { name: 'task_code_fix_001' })).toHaveAttribute(
      'href',
      '/delivery/rd-tasks?task_id=task_code_fix_001',
    );
    expect(within(dialog).getAllByText('inspection.incomplete_source_data').length).toBeGreaterThan(1);
    expect(within(dialog).getByText('src/config.py')).toBeInTheDocument();
  });

  it('opens the report detail dialog from a source_id deep link', async () => {
    const { fetchMock } = installCodeInspectionsFetchMock();
    window.history.pushState({}, '', '/governance/code-inspections?source_id=code_inspection_report_001');

    render(<CodeInspectionsPage />);

    const dialog = await screen.findByRole('dialog', { name: '代码巡检详情' });
    await waitFor(() => expect(within(dialog).getByText('来源链路')).toBeInTheDocument());
    expect(within(dialog).getByText('code_inspection_report_001')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/governance/code-inspections/code_inspection_report_001',
      expect.objectContaining({ method: 'GET' }),
    );
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
    expect(within(dialog).getAllByText('inspection.incomplete_source_data')[0]).toHaveStyle({
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    });
  });

  it('requests and approves a finding suppression from the detail dialog', async () => {
    const { fetchMock } = installCodeInspectionsFetchMock();

    render(<CodeInspectionsPage />);

    await screen.findByText('code_inspection_report_001');
    fireEvent.click(screen.getByRole('button', { name: '详情' }));

    const dialog = await screen.findByRole('dialog', { name: '代码巡检详情' });
    const requestButton = await within(dialog).findByRole('button', { name: '申请忽略' });
    fireEvent.click(requestButton);

    await waitFor(() => expect(within(dialog).getAllByText('待审批').length).toBeGreaterThan(0));
    expect(
      fetchMock,
    ).toHaveBeenCalledWith(
      '/api/governance/code-inspections/code_inspection_report_001/findings/code_inspection_finding_001/suppression-request',
      expect.objectContaining({
        method: 'POST',
      }),
    );

    fireEvent.click(within(dialog).getByRole('button', { name: '批准忽略' }));

    await waitFor(() => expect(within(dialog).getAllByText('已忽略').length).toBeGreaterThan(0));
    expect(
      fetchMock,
    ).toHaveBeenCalledWith(
      '/api/governance/code-inspections/code_inspection_report_001/findings/code_inspection_finding_001/suppression-review',
      expect.objectContaining({
        method: 'POST',
      }),
    );
  });
});
