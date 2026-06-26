import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import { ExecutionTraceLink } from '../src/components/ExecutionTraceLink';

afterEach(() => {
  cleanup();
});

describe('ExecutionTraceLink', () => {
  it('generates execution trace links with both source id and source type', () => {
    render(
      <ExecutionTraceLink sourceId="model_gateway_log_001" sourceType="model_gateway_log">
        调用诊断
      </ExecutionTraceLink>,
    );

    expect(screen.getByRole('link', { name: '调用诊断' })).toHaveAttribute(
      'href',
      '/governance/execution-traces?source_id=model_gateway_log_001&source_type=model_gateway_log',
    );
  });

  it('renders fallback instead of an ambiguous source-id-only link', () => {
    render(
      <ExecutionTraceLink fallback="暂无诊断" sourceId="model_gateway_log_001" sourceType="">
        调用诊断
      </ExecutionTraceLink>,
    );

    expect(screen.queryByRole('link', { name: '调用诊断' })).not.toBeInTheDocument();
    expect(screen.getByText('暂无诊断')).toBeInTheDocument();
  });
});
