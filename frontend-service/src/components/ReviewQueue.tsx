import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { StatusBadge } from '@/components/StatusBadge';
import { usePqls } from '@/hooks/use-pqls';
import { format } from 'date-fns';

interface ReviewQueueProps {
  onSelect: (id: string) => void;
  selectedId: string | null;
  statusFilter?: string;
}

export function ReviewQueue({ onSelect, selectedId, statusFilter }: ReviewQueueProps) {
  const { data: pqls, isLoading } = usePqls();

  const filtered = statusFilter
    ? pqls?.filter((p) => p.status === statusFilter)
    : pqls;

  if (isLoading) return <div className="p-8 text-center text-muted-foreground">Loading…</div>;

  return (
    <div className="rounded-lg border bg-card shadow-sm">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Company</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Score</TableHead>
            <TableHead>Last Active</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {(!filtered || filtered.length === 0) ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                No PQLs found. Upload a CSV to get started.
              </TableCell>
            </TableRow>
          ) : (
            filtered.map((pql) => (
              <TableRow
                key={pql.id}
                className={`cursor-pointer ${selectedId === pql.id ? 'bg-accent' : ''}`}
                onClick={() => onSelect(pql.id)}
              >
                {(() => {
                  const raw = (pql.raw_data || {}) as Record<string, any>;
                  const companyDisplay =
                    pql.company_name ||
                    raw['Company Name'] ||
                    raw['Company name'] ||
                    raw.Company ||
                    raw.company_name ||
                    raw.company ||
                    '—';
                  const lastActiveRaw =
                    raw['Last Active'] ??
                    raw.last_active ??
                    raw.last_active_date ??
                    null;
                  const lastActiveDisplay =
                    lastActiveRaw ??
                    (pql.last_active_date
                      ? format(new Date(pql.last_active_date), 'MMM d, yyyy')
                      : '—');
                  return (
                    <>
                      <TableCell className="font-medium">{companyDisplay}</TableCell>
                      <TableCell className="text-muted-foreground">{pql.email}</TableCell>
                      <TableCell>{pql.product_usage_score ?? '—'}</TableCell>
                      <TableCell className="text-muted-foreground">{lastActiveDisplay}</TableCell>
                      <TableCell><StatusBadge status={pql.status} /></TableCell>
                    </>
                  );
                })()}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
