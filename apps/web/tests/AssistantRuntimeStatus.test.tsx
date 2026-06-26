import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { AssistantRuntimeStatus } from '../src/pages/Assistant/components/AssistantRuntimeStatus';

describe('AssistantRuntimeStatus', () => {
  it('formats checked time with the shared display timezone formatter', () => {
    render(
      <AssistantRuntimeStatus
        checkedAt="2026-06-20T13:02:00+00:00"
        runtimeStatus={{
          chat_gateway: 'configured',
          checks: [
            {
              code: 'redis',
              key: 'redis',
              label: 'Redis',
              remediation: '启动 Redis 后重试。',
              required: true,
              severity: 'critical',
              status: 'failed',
            },
          ],
          embedding_gateway: 'disabled',
          long_memory: 'disabled',
          mode: 'model_gateway',
          model_gateway: 'configured',
          ready: false,
          warnings: [],
        }}
      />,
    );

    expect(screen.getByLabelText('助手运行状态')).toHaveTextContent('检测于 2026-06-20 21:02');
  });
});
