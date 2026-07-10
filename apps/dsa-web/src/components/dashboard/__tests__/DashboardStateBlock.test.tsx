import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DashboardStateBlock } from '../DashboardStateBlock';

describe('DashboardStateBlock', () => {
  it('renders the title as a paragraph by default', () => {
    const { container } = render(<DashboardStateBlock title="Start analysis" description="View tip text" />);

    const title = screen.getByText('Start analysis');
    expect(title.tagName).toBe('P');
    expect(container.querySelector('h3')).toBeNull();
  });

  it('renders the title with the requested heading level', () => {
    render(<DashboardStateBlock title="Start analysis" titleAs="h3" description="View tip text" />);

    expect(screen.getByRole('heading', { name: 'Start analysis', level: 3 })).toBeInTheDocument();
  });

  it('keeps icon, description, action, and loading behaviors intact', () => {
    const { rerender } = render(
      <DashboardStateBlock
        title="Start analysis"
        description="Enter stock code to analyze"
        icon={<span data-testid="icon">icon</span>}
        action={<button type="button">Start now</button>}
      />,
    );

    expect(screen.getByTestId('icon')).toBeInTheDocument();
    expect(screen.getByText('Enter stock code to analyze')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start now' })).toBeInTheDocument();

    rerender(
      <DashboardStateBlock
        title="Start analysis"
        titleAs="h3"
        description="Enter stock code to analyze"
        loading
      />,
    );

    expect(screen.getByRole('heading', { name: 'Start analysis', level: 3 })).toBeInTheDocument();
    expect(screen.getByText('Enter stock code to analyze')).toBeInTheDocument();
    expect(document.querySelector('.home-spinner')).not.toBeNull();
    expect(screen.queryByTestId('icon')).not.toBeInTheDocument();
  });
});
