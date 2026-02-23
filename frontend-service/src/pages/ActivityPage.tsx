import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { format } from 'date-fns';

export default function ActivityPage() {
  const { data: logs, isLoading } = useQuery({
    queryKey: ['activity_log'],
    queryFn: async () => {
      const { data, error } = await supabase.from('activity_log').select('*').order('created_at', { ascending: false }).limit(100);
      if (error) throw error;
      return data;
    },
  });

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Activity Log</h1>
        <p className="text-sm text-muted-foreground">Audit trail of all agent and human actions</p>
      </div>
      <div className="rounded-lg border bg-card shadow-sm">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Time</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>PQL ID</TableHead>
              <TableHead>Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow><TableCell colSpan={4} className="text-center py-8 text-muted-foreground">Loading…</TableCell></TableRow>
            ) : !logs?.length ? (
              <TableRow><TableCell colSpan={4} className="text-center py-8 text-muted-foreground">No activity yet</TableCell></TableRow>
            ) : (
              logs.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="text-muted-foreground whitespace-nowrap">{format(new Date(log.created_at), 'MMM d, HH:mm')}</TableCell>
                  <TableCell className="font-medium">{log.action}</TableCell>
                  <TableCell className="text-xs text-muted-foreground font-mono">{log.pql_id?.slice(0, 8) ?? '—'}</TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-[300px] truncate">{log.details ? JSON.stringify(log.details) : '—'}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
