import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { RunFlowEvent } from '../../../types/runFlow';
import { RunFlowEventList } from '../RunFlowEventList';

const events: RunFlowEvent[] = [
  {
    id: 'evt-1',
    timestamp: '2026-06-08T08:00:01Z',
    severity: 'info',
    type: 'task_created',
    nodeId: 'request',
    title: 'Task created',
  },
  {
    id: 'evt-2',
    timestamp: '2026-06-08T08:00:02Z',
    severity: 'warning',
    type: 'provider_fallback',
    nodeId: 'daily_data',
    title: 'Daily bars fallback',
    message: 'Switched to AkShare after Tushare failed',
  },
  {
    id: 'evt-3',
    timestamp: '2026-06-08T08:00:03Z',
    severity: 'danger',
    type: 'task_cancelled',
    nodeId: 'queue',
    title: 'Task cancelled',
  },
];

describe('RunFlowEventList', () => {
  it('filters fallback and cancellation events with visible text labels', () => {
    render(<RunFlowEventList events={events} />);

    expect(screen.getByText('Task created')).toBeInTheDocument();
    expect(screen.getByText('Daily bars fallback')).toBeInTheDocument();
    expect(screen.getByText('Task cancelled')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Fallback/Retry' }));

    expect(screen.getByText('Daily bars fallback')).toBeInTheDocument();
    expect(screen.queryByText('Task created')).not.toBeInTheDocument();
    expect(screen.queryByText('Task cancelled')).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.getByText('Task cancelled')).toBeInTheDocument();
    expect(screen.queryByText('Daily bars fallback')).not.toBeInTheDocument();
    expect(screen.getByText('Danger')).toBeInTheDocument();
  });

  it('selects the event node when an event row is clicked', () => {
    const onSelectNode = vi.fn();
    render(<RunFlowEventList events={events} onSelectNode={onSelectNode} />);

    fireEvent.click(screen.getByRole('button', { name: 'View event Daily bars fallback related node' }));

    expect(onSelectNode).toHaveBeenCalledWith('daily_data');
  });
});
