import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
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

  it('opens contextual screenshots in a preview dialog', async () => {
    render(<HelpPage />);

    fireEvent.change(screen.getByPlaceholderText('搜索功能、字段或错误码'), {
      target: { value: '系统健康' },
    });
    fireEvent.click(screen.getByRole('button', { name: /系统健康/ }));

    const screenshot = screen.getByRole('img', { name: '系统健康页面总览截图' });
    expect(screenshot).toHaveAttribute(
      'src',
      '/help/screenshots/system-health-overview.png',
    );
    expect(screen.getByText(/依赖状态、优先处理项、分类检查和修复入口/)).toBeInTheDocument();

    fireEvent.click(screenshot);

    const previewDialog = await screen.findByRole('dialog', { name: '图片预览 · 系统健康页面总览截图' });
    expect(within(previewDialog).getByRole('img', { name: '系统健康页面总览截图' })).toHaveAttribute(
      'src',
      '/help/screenshots/system-health-overview.png',
    );
  });
});
