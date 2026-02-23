import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { usePqlDetail } from '@/hooks/use-pqls';
import { Building2 } from 'lucide-react';

interface PqlDetailPanelProps {
  pqlId: string;
  onClose: () => void;
}

export function PqlDetailPanel({ pqlId, onClose }: PqlDetailPanelProps) {
  const { data, isLoading } = usePqlDetail(pqlId);

  if (isLoading) return <div className="p-8 text-center text-muted-foreground">Loading…</div>;
  if (!data) return null;

  const { pql, enrichment } = data;
  const companyInfo = enrichment?.company_info as Record<string, unknown> | null;
  const raw = (pql.raw_data || {}) as Record<string, any>;
  const companyDisplay =
    pql.company_name ||
    raw['Company Name'] ||
    raw['Company name'] ||
    raw.Company ||
    raw.company_name ||
    raw.company ||
    pql.email;

  const renderValue = (value: unknown) => {
    if (value === null || value === undefined || value === '') return 'N/A';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{companyDisplay}</h2>
        <Button variant="ghost" size="sm" onClick={onClose}>✕</Button>
      </div>

      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-1.5">
            <Building2 className="h-4 w-4" /> Company Info
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-1">
          {companyInfo && Object.entries(companyInfo).length > 0 ? (
            Object.entries(companyInfo).map(([key, value]) => (
              <div key={key}>
                <span className="font-medium capitalize">{key.replace(/_/g, ' ')}:</span>{' '}
                {renderValue(value)}
              </div>
            ))
          ) : (
            <div className="text-muted-foreground">No company info available.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
