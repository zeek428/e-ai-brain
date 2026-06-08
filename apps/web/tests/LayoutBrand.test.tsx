import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { layout } from '../src/app';

describe('layout brand action', () => {
  it('shows the IT R&D brain label', () => {
    const actions = layout({}).actionsRender();

    render(<>{actions}</>);

    expect(screen.getByText('IT研发大脑')).toBeInTheDocument();
    expect(screen.queryByText('研发大脑 MVP')).not.toBeInTheDocument();
  });
});
