import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { Modal } from 'antd';
import { afterEach, expect, it, vi } from 'vitest';

import './proComponentsMock';

import { TaskDetailModal } from '../src/pages/TaskCenter/components/TaskDetailModal';
import type { TaskCenterTaskDetailRecord } from '../src/services/aiBrain';

afterEach(() => {
  Modal.destroyAll();
  cleanup();
  vi.restoreAllMocks();
});

const detail = {
  agentLoop: {
    context_manifest_id: 'execution_context_manifest_002',
    context_version: 2,
    cost_budget: 3,
    cost_used: 0.8,
    current_iteration: 2,
    id: 'agent_loop_run_001',
    iterations: [
      {
        change_summary: '补齐参数校验并新增测试',
        context_version: 2,
        failure_analysis: {
          blocked_reasons: [{ code: 'UNIT_TEST_FAILED', message: '第一轮单元测试失败' }],
        },
        id: 'agent_loop_iteration_002',
        iteration_number: 2,
        plan: { steps: ['分析失败', '修改代码', '重新测试'] },
        status: 'executing',
        test_evidence: [{ command: 'npm test', status: 'passed' }],
      },
    ],
    max_duration_seconds: 3600,
    max_iterations: 3,
    status: 'executing',
    token_budget: 100000,
    token_used: 12600,
  },
  createdAt: '2026-07-11 10:00',
  currentStep: 'agent_loop_retrying',
  executionContextManifest: {
    acceptance_criteria: ['登录账号和密码初始值必须为空'],
    branch: 'codex/login-security',
    bug_refs: [{ id: 'bug_114', title: '登录页存在硬编码凭据' }],
    content_hash: 'abc123',
    created_at: '2026-07-11T02:00:00Z',
    id: 'execution_context_manifest_002',
    knowledge_refs: [
      {
        content_truncated: false,
        document_id: 'knowledge_document_001',
        document_version: 3,
        retrieval_reason: '产品与版本权限范围匹配',
        title: '认证安全规范',
      },
    ],
    repository_ref: { name: 'e-ai-brain', remote_url: 'https://example.test/e-ai-brain.git' },
    requirement_refs: [{ id: 'requirement_084', title: '移除默认登录凭据' }],
    retrieval_summary: { selected_knowledge_count: 1 },
    truncation_summary: { truncated_knowledge_count: 0 },
    version: 2,
  },
  graphRunIds: ['graph_run_001'],
  id: 'task_273',
  inputJson: {},
  label: '修复硬编码敏感凭据',
  moduleName: '登录认证',
  outputJson: { summary: '执行中' },
  outputSummary: '执行中',
  owner: 'user_admin',
  product: '研发大脑',
  productId: 'product_119',
  productName: '研发大脑',
  qualityGate: {
    blocked_reasons: [{ code: 'UNIT_TEST_FAILED', message: '单元测试未通过' }],
    checks: [
      {
        check_type: 'unit_test',
        evidence_ref: 'platform://quality/unit-test/001',
        independent: true,
        source: 'platform_verifier',
        status: 'failed',
        summary: '18 passed, 1 failed',
      },
      {
        check_type: 'secret_scan',
        evidence_ref: 'platform://quality/secret-scan/001',
        independent: true,
        source: 'platform_scan',
        status: 'passed',
        summary: '未发现凭据',
      },
    ],
    id: 'quality_gate_run_001',
    independent_evidence_count: 2,
    risk_level: 'medium',
    status: 'blocked',
    summary: '独立质量门禁未通过',
  },
  requirementTitle: '移除默认登录凭据',
  status: 'running',
  type: 'development_planning',
  versionName: '2026.07',
} as unknown as TaskCenterTaskDetailRecord;

it('presents Agent loop, quality gate and context manifest as structured governance views', async () => {
  const onTakeover = vi.fn(async () => undefined);
  render(
    <TaskDetailModal
      dialog={{
        detail,
        loading: false,
        task: detail,
      }}
      onClose={vi.fn()}
      onRequestAgentTakeover={onTakeover}
      taskStatusLabels={{ running: { color: 'blue', label: '运行中' } }}
      taskTypeLabels={{ development_planning: '代码实现 / 开发计划' }}
    />,
  );

  fireEvent.click(screen.getByRole('tab', { name: '自治循环' }));
  expect(screen.getByText('第 2 轮')).toBeInTheDocument();
  expect(screen.getByText('补齐参数校验并新增测试')).toBeInTheDocument();
  expect(screen.getByText('第一轮单元测试失败')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '转人工接管' }));
  fireEvent.click(await screen.findByRole('button', { name: '确认接管' }));
  await waitFor(() => expect(onTakeover).toHaveBeenCalledTimes(1));

  fireEvent.click(screen.getByRole('tab', { name: '质量门禁' }));
  expect(screen.getByText('独立质量门禁未通过')).toBeInTheDocument();
  expect(screen.getByText('18 passed, 1 failed')).toBeInTheDocument();
  expect(screen.getAllByText('平台独立证据').length).toBeGreaterThan(0);

  fireEvent.click(screen.getByRole('tab', { name: '执行上下文' }));
  expect(screen.getByText('登录账号和密码初始值必须为空')).toBeInTheDocument();
  expect(screen.getByText('认证安全规范')).toBeInTheDocument();
  expect(screen.getByText('产品与版本权限范围匹配')).toBeInTheDocument();
  expect(screen.getByText('codex/login-security')).toBeInTheDocument();
});
