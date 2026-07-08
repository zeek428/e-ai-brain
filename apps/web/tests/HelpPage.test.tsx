import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import './proComponentsMock';

import HelpPage from '../src/pages/Help';

describe('HelpPage', () => {
  afterEach(() => {
    cleanup();
    window.history.pushState({}, '', '/');
  });

  it('renders searchable help manuals and opens target modules', () => {
    render(<HelpPage />);

    expect(screen.getByRole('heading', { level: 1, name: /帮助中心/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: '快速开始' })).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText('搜索功能、字段或错误码'), {
      target: { value: '知识中心' },
    });
    fireEvent.click(screen.getByRole('button', { name: /知识中心/ }));

    expect(screen.getByRole('heading', { level: 2, name: '知识中心' })).toBeInTheDocument();
    expect(screen.getByText(/Hybrid Search/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '进入功能' }));
    expect(window.location.pathname).toBe('/assets/knowledge');
  });

  it('shows useful empty state when no manual matches the search', () => {
    render(<HelpPage />);

    fireEvent.change(screen.getByPlaceholderText('搜索功能、字段或错误码'), {
      target: { value: 'not-a-real-help-keyword' },
    });

    expect(screen.getByText('没有找到匹配的帮助文档')).toBeInTheDocument();
  });
});
