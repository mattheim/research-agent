import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { usePqls } from '@/hooks/use-pqls';
import { PQL_STATUSES, type PqlStatus } from '@/lib/constants';
import { Clock, CheckCircle2, Sparkles, Send, XCircle } from 'lucide-react';

const icons: Record<string, React.ElementType> = {
  pending: Clock,
  qualified: CheckCircle2,
  enriched: Sparkles,
  sent: Send,
  rejected: XCircle,
};

export function PipelineOverview() {
  const { data: pqls } = usePqls();

  const counts = Object.keys(PQL_STATUSES).reduce((acc, status) => {
    acc[status] = pqls?.filter((p) => p.status === status).length ?? 0;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
      {Object.entries(PQL_STATUSES).map(([key, config]) => {
        const Icon = icons[key] ?? Clock;
        return (
          <Card key={key} className="border-0 shadow-sm">
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                <Icon className="h-3.5 w-3.5" />
                {config.label}
              </CardTitle>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-2xl font-bold">{counts[key]}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
