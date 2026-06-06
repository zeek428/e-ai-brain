import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  approveManagementRequirement,
  approveTaskCenterReview,
  batchScheduleRequirements,
  createAutomatedTestingTask,
  createCodeReviewTask,
  createDevelopmentPlanningTask,
  createManagementBug,
  createManagementKnowledgeDocument,
  createManagementProduct,
  createManagementRequirement,
  createManagementUser,
  createPostReleaseAnalysisTask,
  createReleaseReadinessTask,
  createTechnicalSolutionTask,
  deleteManagementBug,
  deleteManagementKnowledgeDocument,
  deleteManagementProduct,
  deleteManagementRequirement,
  deleteManagementUser,
  fetchCodeReviewReport,
  fetchProductGitRepositories,
  fetchTaskMarkdown,
  generateRequirementTask,
  previewGitLabMergeRequest,
  rejectManagementRequirement,
  snapshotGitLabMergeRequest,
  startTaskCenterTask,
  updateManagementBug,
  updateManagementKnowledgeDocument,
  updateManagementProduct,
  updateManagementRequirement,
  updateManagementUser,
} from '../src/services/aiBrain';

afterEach(() => {
  window.localStorage.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('management CRUD service API mappings', () => {
  it('sends management CRUD mutations to backend APIs with the stored token', async () => {
    const jsonResponse = (body: unknown) =>
      new Response(JSON.stringify(body), {
        headers: { 'Content-Type': 'application/json' },
        status: 200,
      });
    const fetchMock = vi.fn<typeof fetch>(async (input, init) => {
      expect(init?.headers).toMatchObject({ Authorization: 'Bearer token-admin' });
      if (input === '/api/export/tasks/task_solution/markdown') {
        return new Response('# Markdown 导出', {
          headers: { 'Content-Type': 'text/markdown' },
          status: 200,
        });
      }
      if (input === '/api/products/product_api/git-repositories?active_only=true') {
        return jsonResponse({
          data: {
            items: [
              {
                git_provider: 'gitlab',
                id: 'repo_api',
                name: 'AI Brain API',
                project_path: 'platform/ai-brain',
                status: 'active',
              },
            ],
            total: 1,
          },
        });
      }
      if (input === '/api/devops/gitlab/merge-requests/repo_api/42/preview') {
        return jsonResponse({
          data: {
            author: 'alice',
            changed_file_count: 3,
            mr_iid: 42,
            repository_id: 'repo_api',
            title: 'feat: review flow',
          },
        });
      }
      if (input === '/api/devops/gitlab/merge-requests/repo_api/42/snapshot') {
        return jsonResponse({
          data: {
            id: 'snapshot_api',
            mr_iid: 42,
            repository_id: 'repo_api',
          },
        });
      }
      if (input === '/api/ai-tasks/task_code_review/code-review-report') {
        return jsonResponse({
          data: {
            findings: [{ severity: 'high', summary: '缺少边界测试' }],
            gitlab_writeback_performed: false,
            id: 'report_api',
            risk_level: 'medium',
            status: 'pending_review',
            summary: '发现 1 个高风险问题',
          },
        });
      }
      if (input === '/api/requirements/batch-schedule') {
        return jsonResponse({
          data: {
            batch_id: 'requirement_batch_api',
            product_id: 'product_api',
            skipped: [],
            skipped_count: 0,
            updated: [
              {
                content: '需求内容',
                created_at: '2026-06-04T08:00:00+00:00',
                id: 'requirement_api',
                priority: 'P1',
                product_code: 'CRUD',
                product_id: 'product_api',
                status: 'planned',
                title: 'CRUD 需求',
                updated_at: '2026-06-04T08:30:00+00:00',
                version_id: 'version_api',
                version_name: 'v1',
              },
            ],
            updated_count: 1,
            version_id: 'version_api',
          },
        });
      }
      return jsonResponse({
        data: {
          id: String(input).includes('/api/products') ? 'product_api' : 'resource_api',
          status: 'active',
        },
      });
    });
    window.localStorage.setItem('ai_brain_access_token', 'token-admin');
    vi.stubGlobal('fetch', fetchMock);

    await createManagementProduct({ code: 'CRUD', name: 'CRUD 产品', status: 'active' });
    await updateManagementProduct('product_api', { name: '更新产品' });
    await deleteManagementProduct('product_api');
    await createManagementRequirement({
      content: '需求内容',
      priority: 'P1',
      product_id: 'product_api',
      title: 'CRUD 需求',
      version_id: 'version_api',
    });
    await updateManagementRequirement('requirement_api', { title: '更新需求' });
    await approveManagementRequirement('requirement_api');
    await rejectManagementRequirement('requirement_api', '目标不清晰');
    await generateRequirementTask('requirement_api');
    await deleteManagementRequirement('requirement_api');
    await createManagementBug({
      description: 'Bug 描述',
      product_id: 'product_api',
      severity: 'major',
      source: 'manual_test',
      title: 'CRUD Bug',
    });
    await updateManagementBug('bug_api', { assignee: 'rd_owner@example.com' });
    await deleteManagementBug('bug_api');
    await createManagementKnowledgeDocument({
      content: '知识内容',
      permission_roles: ['admin'],
      title: 'CRUD 知识',
    });
    await updateManagementKnowledgeDocument('knowledge_api', { title: '更新知识' });
    await deleteManagementKnowledgeDocument('knowledge_api');
    await createManagementUser({
      display_name: 'CRUD 用户',
      password: 'secret123',
      roles: ['viewer'],
      status: 'active',
      username: 'crud@example.com',
    });
    await updateManagementUser('user_api', { display_name: '更新用户' });
    await deleteManagementUser('user_api');
    await startTaskCenterTask('task_api');
    await approveTaskCenterReview('review_api', 1);
    await createTechnicalSolutionTask({
      createdAt: '2026-06-03 09:00',
      id: 'task_design',
      label: '产品详细设计：CRUD 需求',
      owner: 'user_admin',
      product: 'AI Brain',
      productId: 'product_api',
      requirementId: 'requirement_api',
      status: 'completed',
      type: 'product_detail_design',
    });
    await createDevelopmentPlanningTask({
      createdAt: '2026-06-03 09:00',
      id: 'task_solution',
      label: '技术方案：CRUD 需求',
      owner: 'user_admin',
      product: 'AI Brain',
      productId: 'product_api',
      requirementId: 'requirement_api',
      status: 'completed',
      type: 'technical_solution',
    });
    await createAutomatedTestingTask({
      createdAt: '2026-06-03 09:00',
      id: 'task_solution',
      label: '技术方案：CRUD 需求',
      owner: 'user_admin',
      product: 'AI Brain',
      productId: 'product_api',
      requirementId: 'requirement_api',
      status: 'completed',
      type: 'technical_solution',
    });
    await createReleaseReadinessTask({
      createdAt: '2026-06-03 09:00',
      id: 'task_solution',
      label: '技术方案：CRUD 需求',
      owner: 'user_admin',
      product: 'AI Brain',
      productId: 'product_api',
      requirementId: 'requirement_api',
      status: 'completed',
      type: 'technical_solution',
    });
    await createPostReleaseAnalysisTask({
      createdAt: '2026-06-03 09:00',
      id: 'task_release',
      label: '发布评估：CRUD 需求',
      owner: 'user_admin',
      product: 'AI Brain',
      productId: 'product_api',
      requirementId: 'requirement_api',
      status: 'completed',
      type: 'release_readiness',
    });
    await expect(fetchTaskMarkdown('task_solution')).resolves.toBe('# Markdown 导出');
    await fetchProductGitRepositories('product_api');
    await previewGitLabMergeRequest('repo_api', 42);
    await snapshotGitLabMergeRequest({
      mrIid: 42,
      repositoryId: 'repo_api',
      requirementId: 'requirement_api',
      technicalSolutionTaskId: 'task_solution',
    });
    await createCodeReviewTask(
      {
        createdAt: '2026-06-03 09:00',
        id: 'task_solution',
        label: '技术方案：CRUD 需求',
        owner: 'user_admin',
        product: 'AI Brain',
        productId: 'product_api',
        requirementId: 'requirement_api',
        status: 'completed',
        type: 'technical_solution',
      },
      'snapshot_api',
      42,
    );
    await expect(fetchCodeReviewReport('task_code_review')).resolves.toMatchObject({
      gitlabWritebackPerformed: false,
      riskLevel: 'medium',
      status: 'pending_review',
    });
    const batchScheduleResult = await batchScheduleRequirements({
      product_id: 'product_api',
      reason: '纳入 CRUD 版本',
      requirement_ids: ['requirement_api'],
      version_id: 'version_api',
    });
    expect(batchScheduleResult.batchId).toBe('requirement_batch_api');
    expect(batchScheduleResult.updatedCount).toBe(1);

    expect(fetchMock.mock.calls.map(([path, init]) => [path, init?.method])).toEqual([
      ['/api/products', 'POST'],
      ['/api/products/product_api', 'PATCH'],
      ['/api/products/product_api', 'DELETE'],
      ['/api/requirements', 'POST'],
      ['/api/requirements/requirement_api', 'PATCH'],
      ['/api/requirements/requirement_api/approve', 'POST'],
      ['/api/requirements/requirement_api/reject', 'POST'],
      ['/api/requirements/requirement_api/generate-task', 'POST'],
      ['/api/requirements/requirement_api', 'DELETE'],
      ['/api/bugs', 'POST'],
      ['/api/bugs/bug_api', 'PATCH'],
      ['/api/bugs/bug_api', 'DELETE'],
      ['/api/knowledge/documents', 'POST'],
      ['/api/knowledge/documents/knowledge_api', 'PATCH'],
      ['/api/knowledge/documents/knowledge_api', 'DELETE'],
      ['/api/users', 'POST'],
      ['/api/users/user_api', 'PATCH'],
      ['/api/users/user_api', 'DELETE'],
      ['/api/ai-tasks/task_api/start', 'POST'],
      ['/api/reviews/review_api/approve', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/export/tasks/task_solution/markdown', 'GET'],
      ['/api/products/product_api/git-repositories?active_only=true', 'GET'],
      ['/api/devops/gitlab/merge-requests/repo_api/42/preview', 'GET'],
      ['/api/devops/gitlab/merge-requests/repo_api/42/snapshot', 'POST'],
      ['/api/ai-tasks', 'POST'],
      ['/api/ai-tasks/task_code_review/code-review-report', 'GET'],
      ['/api/requirements/batch-schedule', 'POST'],
    ]);
    expect(fetchMock.mock.calls[20]?.[1]?.body).toBe(
      JSON.stringify({
        input: { product_detail_design_task_id: 'task_design' },
        requirement_id: 'requirement_api',
        task_type: 'technical_solution',
        title: '技术方案：CRUD 需求',
      }),
    );
    expect(fetchMock.mock.calls[21]?.[1]?.body).toBe(
      JSON.stringify({
        input: { technical_solution_task_id: 'task_solution' },
        requirement_id: 'requirement_api',
        task_type: 'development_planning',
        title: '开发计划：CRUD 需求',
      }),
    );
    expect(fetchMock.mock.calls[22]?.[1]?.body).toBe(
      JSON.stringify({
        input: { technical_solution_task_id: 'task_solution' },
        requirement_id: 'requirement_api',
        task_type: 'automated_testing',
        title: '自动化测试：CRUD 需求',
      }),
    );
    expect(fetchMock.mock.calls[23]?.[1]?.body).toBe(
      JSON.stringify({
        input: { technical_solution_task_id: 'task_solution' },
        requirement_id: 'requirement_api',
        task_type: 'release_readiness',
        title: '发布评估：CRUD 需求',
      }),
    );
    expect(fetchMock.mock.calls[24]?.[1]?.body).toBe(
      JSON.stringify({
        input: { release_readiness_task_id: 'task_release' },
        requirement_id: 'requirement_api',
        task_type: 'post_release_analysis',
        title: '上线后分析：CRUD 需求',
      }),
    );
    expect(fetchMock.mock.calls[28]?.[1]?.body).toBe(
      JSON.stringify({
        requirement_id: 'requirement_api',
        technical_solution_task_id: 'task_solution',
      }),
    );
    expect(fetchMock.mock.calls[29]?.[1]?.body).toBe(
      JSON.stringify({
        input: { gitlab_mr_snapshot_id: 'snapshot_api' },
        requirement_id: 'requirement_api',
        task_type: 'code_review',
        title: 'Code Review：CRUD 需求 MR !42',
      }),
    );
    expect(fetchMock.mock.calls[31]?.[1]?.body).toBe(
      JSON.stringify({
        product_id: 'product_api',
        reason: '纳入 CRUD 版本',
        requirement_ids: ['requirement_api'],
        version_id: 'version_api',
      }),
    );
  });
});
