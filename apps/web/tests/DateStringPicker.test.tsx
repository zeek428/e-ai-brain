import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { DateStringPicker } from '../src/components/DateStringPicker';

describe('DateStringPicker', () => {
  it('does not clear an existing date when blur carries an empty value', () => {
    const handleChange = vi.fn();

    render(
      <DateStringPicker
        onChange={handleChange}
        placeholder="请选择计划发布时间"
        value="2026-06-30"
      />,
    );

    fireEvent.blur(screen.getByPlaceholderText('请选择计划发布时间'), {
      target: { value: '' },
    });

    expect(handleChange).not.toHaveBeenCalled();
  });
});
