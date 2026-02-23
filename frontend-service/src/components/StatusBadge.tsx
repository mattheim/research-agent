import { PQL_STATUSES, type PqlStatus } from '@/lib/constants';
import { cn } from '@/lib/utils';
import { CheckCircle2, Clock, Send, X } from 'lucide-react';

export function StatusBadge({ status }: { status: string }) {
  const config = PQL_STATUSES[status as PqlStatus] ?? {
    label: status,
    color: 'bg-muted text-muted-foreground',
  };

  let Icon = Clock;
  let iconColor = 'text-muted-foreground';

  if (status === 'qualified') {
    Icon = CheckCircle2;
    iconColor = 'text-emerald-500';
  } else if (status === 'pending') {
    Icon = Clock;
    iconColor = 'text-yellow-500';
  } else if (status === 'rejected') {
    Icon = X;
    iconColor = 'text-red-500';
  } else if (status === 'sent') {
    Icon = Send;
    iconColor = 'text-blue-500';
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold',
        config.color,
      )}
    >
      <Icon className={cn('h-3.5 w-3.5', iconColor)} />
      {config.label}
    </span>
  );
}
