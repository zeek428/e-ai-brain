import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { VersionDashboardCollaborationPanel } from '../src/pages/IterationVersions/components/VersionDashboardCollaborationPanel';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe('VersionDashboardCollaborationPanel', () => {
  it('shows frozen capacity and serialized resource-conflict evidence in the version overview', () => {
    render(
      <VersionDashboardCollaborationPanel
        onAction={vi.fn()}
        overview={{
          action: { label: '继续研发协同', runId: 'run_001', type: 'continue' },
          activeRun: {
            blockedWorkItemCount: 0,
            capacity: { available: 1, frozen: 2, used: 1 },
            deliveryTarget: 'ready_for_release',
            id: 'run_001',
            parallelConflictCount: 1,
            pendingDecisionCount: 0,
            roleCodes: ['developer'],
            runGeneration: 1,
            scopeVersion: 1,
            seatCount: 1,
            status: 'running',
            totalWorkItemCount: 2,
            waitingHumanWorkItemCount: 0,
          },
        }}
      />,
    );

    expect(screen.getByText('可用 AI 席位：1 / 2')).toBeInTheDocument();
    expect(screen.getByText('已串行化资源冲突：1')).toBeInTheDocument();
  });

  it('shows the active R&D collaboration summary and continues it from the version overview', () => {
    const onAction = vi.fn();

    render(
      <VersionDashboardCollaborationPanel
        onAction={onAction}
        overview={{
          action: {
            label: '继续研发协同',
            runId: 'run_001',
            type: 'continue',
          },
          activeRun: {
            blockedWorkItemCount: 1,
            capacity: { available: 1, frozen: 2, used: 1 },
            deliveryTarget: 'ready_for_release',
            id: 'run_001',
            parallelConflictCount: 0,
            pendingDecisionCount: 1,
            roleCodes: ['developer', 'tester'],
            runGeneration: 1,
            scopeVersion: 3,
            seatCount: 2,
            status: 'waiting_human',
            totalWorkItemCount: 4,
            waitingHumanWorkItemCount: 1,
          },
        }}
      />,
    );

    expect(screen.getByText('研发协同')).toBeInTheDocument();
    expect(screen.getByText('waiting_human')).toBeInTheDocument();
    expect(screen.getByText('开发员工、测试员工')).toBeInTheDocument();
    expect(screen.getByText('4 个')).toBeInTheDocument();
    expect(screen.getAllByText('1 个')).toHaveLength(3);

    fireEvent.click(screen.getByRole('button', { name: '继续研发协同' }));
    expect(onAction).toHaveBeenCalledWith({
      label: '继续研发协同',
      runId: 'run_001',
      type: 'continue',
    });
  });
});
