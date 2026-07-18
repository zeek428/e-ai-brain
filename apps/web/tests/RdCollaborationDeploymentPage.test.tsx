import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { DeploymentPanel } from '../src/pages/RdCollaboration/DeploymentPanel';

describe('DeploymentPanel', () => {
  it('only links to the existing deployment domain after a deployed-target run reaches ready for release', () => {
    const { rerender } = render(
      <DeploymentPanel run={{ delivery_target: 'ready_for_release', product_version_id: 'version_001', status: 'completed' }} />,
    );
    expect(screen.queryByRole('link', { name: '查看既有部署请求' })).not.toBeInTheDocument();

    rerender(
      <DeploymentPanel run={{ delivery_target: 'deployed', product_version_id: 'version_001', status: 'ready_for_release' }} />,
    );
    expect(screen.getByRole('link', { name: '查看既有部署请求' })).toHaveAttribute(
      'href',
      '/governance/deployments?version_id=version_001',
    );
    expect(screen.queryByRole('button', { name: /部署|创建/ })).not.toBeInTheDocument();
  });
});
