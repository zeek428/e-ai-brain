import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { TaskOutputSummary } from '../src/pages/TaskCenter/components/TaskOutputSummary';

describe('TaskOutputSummary', () => {
  it('renders Markdown tables as readable table cells', () => {
    render(
      <TaskOutputSummary
        summary={[
          '| 页面区域 | 展示字段 |',
          '|---|---|',
          '| 协同总览 | 运行编号 |',
          '| 测试证据 | 门禁状态 |',
        ].join('\n')}
      />,
    );

    const table = screen.getByRole('table');
    expect(within(table).getByRole('columnheader', { name: '页面区域' })).toBeInTheDocument();
    expect(within(table).getByRole('columnheader', { name: '展示字段' })).toBeInTheDocument();
    expect(within(table).getByRole('cell', { name: '协同总览' })).toBeInTheDocument();
    expect(within(table).getByRole('cell', { name: '门禁状态' })).toBeInTheDocument();
  });
});
