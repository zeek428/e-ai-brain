import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AssistantBubble } from '../src/pages/Assistant/components/AssistantMessageBubble';
import { AssistantReferenceContext } from '../src/pages/Assistant/components/AssistantReferenceContext';
import { assistantReferenceFullChainHref } from '../src/pages/Assistant/components/referencePresentation';

afterEach(() => {
  cleanup();
});

describe('AI assistant full-chain links', () => {
  it('derives requirement full-chain hrefs for delivery references', () => {
    expect(
      assistantReferenceFullChainHref({
        id: 'version_assistant',
        title: 'AI 助手迭代',
        type: 'iteration_version',
        url: '/delivery/versions?version_id=version_assistant',
      }),
    ).toBe('/delivery/full-chain?subject_id=version_assistant&subject_type=iteration_version');
    expect(
      assistantReferenceFullChainHref({
        id: 'version_product',
        title: '产品版本',
        type: 'product_version',
        url: '/delivery/versions?version_id=version_product',
      }),
    ).toBe('/delivery/full-chain?subject_id=version_product&subject_type=product_version');
    expect(
      assistantReferenceFullChainHref({
        id: 'branch_config_assistant',
        title: 'AI 助手分支',
        type: 'product_version_branch_config',
        url: '/delivery/versions?branch_config_id=branch_config_assistant',
      }),
    ).toBe(
      '/delivery/full-chain?subject_id=branch_config_assistant&subject_type=product_version_branch_config',
    );
    expect(
      assistantReferenceFullChainHref({
        id: 'scheduled_job_001',
        title: '每周反馈抽取',
        type: 'scheduled_job',
        url: '/tasks/scheduled-jobs?job_id=scheduled_job_001',
      }),
    ).toBeUndefined();
  });

  it('shows full-chain entry on selected assistant references and detail modal', () => {
    render(
      <AssistantReferenceContext
        isExpanded
        selectedReferences={[
          {
            id: 'requirement_assistant',
            summary: 'AI 助手交付需求',
            title: 'AI 助手交付需求',
            type: 'requirement',
            url: '/delivery/requirements?requirement_id=requirement_assistant',
          },
          {
            id: 'scheduled_job_feedback',
            title: '每周反馈抽取',
            type: 'scheduled_job',
            url: '/tasks/scheduled-jobs?job_id=scheduled_job_feedback',
          },
        ]}
        onRemoveReference={vi.fn()}
        onToggleExpanded={vi.fn()}
      />,
    );

    const context = screen.getByLabelText('本次上下文');
    expect(within(context).getByRole('link', { name: '全链路' })).toHaveAttribute(
      'href',
      '/delivery/full-chain?subject_id=requirement_assistant&subject_type=requirement',
    );
    expect(within(context).getAllByRole('link', { name: '全链路' })).toHaveLength(1);

    fireEvent.click(within(context).getByRole('button', { name: '查看摘要 AI 助手交付需求' }));
    expect(screen.getByRole('link', { name: '查看全链路' })).toHaveAttribute(
      'href',
      '/delivery/full-chain?subject_id=requirement_assistant&subject_type=requirement',
    );
  });

  it('shows full-chain entry on assistant message references', () => {
    render(
      <AssistantBubble
        draftResolutionById={{}}
        draftStatusById={{}}
        message={{
          content: '当前已进入 AI 助手迭代开发。',
          id: 'assistant_message_api',
          references: [
            {
              id: 'task_api',
              title: 'AI 助手任务',
              type: 'ai_task',
              url: '/delivery/rd-tasks?task_id=task_api',
            },
          ],
          role: 'assistant',
          toolResults: [],
        }}
        resultWriteTargetLabels={new Map()}
        scheduledJobRunById={{}}
        onCancelDraft={vi.fn()}
        onConfirmDraft={vi.fn()}
        onRegenerateDraft={vi.fn()}
        onRestoreFailedRequest={vi.fn()}
        onRetryFailedRequest={vi.fn()}
        onUseConnectionFollowupPrompt={vi.fn()}
        onUseRunCardFollowupPrompt={vi.fn()}
        onUseRunFollowupPrompt={vi.fn()}
        onUseTaskGuidePrompt={vi.fn()}
        onViewDraft={vi.fn()}
      />,
    );

    expect(screen.getByRole('link', { name: /AI 助手任务/ })).toHaveAttribute(
      'href',
      '/delivery/rd-tasks?task_id=task_api',
    );
    expect(screen.getByRole('link', { name: '全链路' })).toHaveAttribute(
      'href',
      '/delivery/full-chain?subject_id=task_api&subject_type=ai_task',
    );
  });
});
