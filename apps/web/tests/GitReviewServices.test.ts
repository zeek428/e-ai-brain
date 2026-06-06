import { afterEach, describe, expect, it, vi } from 'vitest';

import { previewCodeReviewPullRequest, snapshotCodeReviewPullRequest } from '../src/services/aiBrain';

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('GitHub code review service API mappings', () => {
  it('routes GitHub code review preview and snapshot requests to GitHub PR APIs', async () => {
    const fetchMock = vi.fn<typeof fetch>(async (input) => {
      if (input === '/api/devops/github/pull-requests/repo_github/3/preview') {
        return new Response(
          JSON.stringify({
            data: {
              author: { login: 'zeek428' },
              changed_file_count: 2,
              changed_files_summary: [
                { additions: 3, deletions: 1, path: 'apps/api/app/main.py' },
              ],
              diff_file_tree: [
                { additions: 3, deletions: 1, file_count: 1, path: 'apps' },
              ],
              mr_iid: 3,
              repository_id: 'repo_github',
              review_checklist: ['确认变更文件归属目标需求和技术方案范围'],
              risk_summary: {
                file_count: 1,
                largest_file: {
                  additions: 3,
                  deletions: 1,
                  line_count: 4,
                  path: 'apps/api/app/main.py',
                },
                risk_level: 'low',
                total_additions: 3,
                total_changed_lines: 4,
                total_deletions: 1,
              },
              source_branch: 'feature/github-pr',
              target_branch: 'main',
              title: '真实 GitHub PR',
              web_url: 'https://github.com/zeek428/e-ai-brain/pull/3',
              writeback_allowed: false,
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      if (input === '/api/devops/github/pull-requests/repo_github/3/snapshot') {
        return new Response(
          JSON.stringify({
            data: {
              diff_limit_bytes: 204800,
              diff_size_bytes: 1024,
              id: 'snapshot_github',
              mr_iid: 3,
              repository_id: 'repo_github',
            },
          }),
          { headers: { 'Content-Type': 'application/json' }, status: 200 },
        );
      }
      throw new Error(`Unexpected fetch call: ${String(input)}`);
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);
    const repository = {
      defaultBranch: 'main',
      id: 'repo_github',
      label: 'GitHub 仓库',
      name: 'GitHub 仓库',
      projectPath: 'zeek428/e-ai-brain',
      provider: 'github',
      status: 'active',
    };

    await expect(previewCodeReviewPullRequest(repository, 3)).resolves.toMatchObject({
      diffFileTree: [{ additions: 3, deletions: 1, fileCount: 1, path: 'apps' }],
      mrIid: 3,
      reviewChecklist: ['确认变更文件归属目标需求和技术方案范围'],
      riskSummary: expect.objectContaining({ riskLevel: 'low', totalChangedLines: 4 }),
      title: '真实 GitHub PR',
    });
    await expect(
      snapshotCodeReviewPullRequest({
        mrIid: 3,
        repository,
        requirementId: 'requirement_api',
        technicalSolutionTaskId: 'task_solution',
      }),
    ).resolves.toMatchObject({ id: 'snapshot_github', mrIid: 3 });

    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method ?? 'GET'])).toEqual([
      ['/api/devops/github/pull-requests/repo_github/3/preview', 'GET'],
      ['/api/devops/github/pull-requests/repo_github/3/snapshot', 'POST'],
    ]);
  });
});
