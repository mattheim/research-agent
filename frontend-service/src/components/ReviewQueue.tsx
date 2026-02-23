import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { usePqls } from '@/hooks/use-pqls';

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
            <TableHead>Name</TableHead>
            <TableHead>Company</TableHead>
            <TableHead>Email</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {!filtered || filtered.length === 0 ? (
            <TableRow>
              <TableCell colSpan={3} className="text-center text-muted-foreground py-8">
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
                  const firstName =
                    raw.first_name ||
                    raw.firstName ||
                    raw['First Name'] ||
                    raw['first name'] ||
                    '';
                  const lastName =
                    raw.last_name ||
                    raw.lastName ||
                    raw['Last Name'] ||
                    raw['last name'] ||
                    '';
                  const combinedName = `${String(firstName).trim()} ${String(lastName).trim()}`.trim();
                  const nameDisplay =
                    raw.name ||
                    raw.Name ||
                    raw.full_name ||
                    raw.fullName ||
                    raw['Full Name'] ||
                    combinedName ||
                    '—';
                  const companyDisplay =
                    pql.company_name ||
                    raw['Company Name'] ||
                    raw['Company name'] ||
                    raw.Company ||
                    raw.company_name ||
                    raw.company ||
                    '—';

                  return (
                    <>
                      <TableCell className="font-medium">{String(nameDisplay)}</TableCell>
                      <TableCell className="font-medium">{companyDisplay}</TableCell>
                      <TableCell className="text-muted-foreground">{pql.email}</TableCell>
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
