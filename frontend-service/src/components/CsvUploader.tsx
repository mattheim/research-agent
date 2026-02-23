import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useInsertPqls } from '@/hooks/use-pqls';
import { Upload, FileSpreadsheet, Loader2 } from 'lucide-react';
import {
  AGENTS_API_BASE_URL,
  getStoredQualificationThreshold,
  normalizeQualificationThreshold,
  setStoredQualificationThreshold,
} from '@/lib/constants';
import { toast } from '@/hooks/use-toast';

interface ParsedRow {
  [key: string]: string;
}

export function CsvUploader() {
  const [rows, setRows] = useState<ParsedRow[]>([]);
  const [headers, setHeaders] = useState<string[]>([]);
  const [fileName, setFileName] = useState('');
  const [processing, setProcessing] = useState(false);
  const [singleId, setSingleId] = useState('');
  const [singleEmail, setSingleEmail] = useState('');
  const [singleCompany, setSingleCompany] = useState('');
  const [singleUsage, setSingleUsage] = useState('');
  const [qualificationThreshold, setQualificationThreshold] = useState<number>(
    getStoredQualificationThreshold(),
  );
  const insertPqls = useInsertPqls();

  const handleFile = useCallback((file: File) => {
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);
      if (lines.length < 2) return;
      const hdrs = lines[0].split(',').map((h) => h.trim().replace(/^"|"$/g, ''));
      setHeaders(hdrs);
      const parsed = lines.slice(1).map((line) => {
        const vals = line.split(',').map((v) => v.trim().replace(/^"|"$/g, ''));
        const row: ParsedRow = {};
        hdrs.forEach((h, i) => { row[h] = vals[i] ?? ''; });
        return row;
      });
      setRows(parsed);
    };
    reader.readAsText(file);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleTestAgentsApi = async () => {
    try {
      const resp = await fetch(`${AGENTS_API_BASE_URL}/llm-test`);
      if (!resp.ok) throw new Error(`Status ${resp.status}`);
      const data = await resp.json();
      console.log('LLM test result:', data);
      toast({ title: 'Agents API OK', description: 'Successfully called LLM via Agents API.' });
    } catch (e: any) {
      toast({
        title: 'Agents API test failed',
        description: e.message,
        variant: 'destructive',
      });
    }
  };

  const runAgentsEnrichment = async (inserted: any[]) => {
    try {
      let processed = 0;
      for (const pql of inserted) {
        const response = await fetch(`${AGENTS_API_BASE_URL}/research?pql_id=${pql.id}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            qualification_threshold: qualificationThreshold,
          }),
        });
        if (!response.ok) {
          throw new Error(`Status ${response.status} while enriching ${pql.id}`);
        }
        processed += 1;
      }
      toast({ title: `${processed} PQLs enriched` });
    } catch {
      toast({
        title: 'Agents API not reachable',
        description: 'PQLs saved but not yet enriched. Start your local API to process them.',
        variant: 'destructive',
      });
    }
  };

  const handleThresholdChange = (rawValue: string) => {
    const parsed = Number(rawValue);
    const normalized = setStoredQualificationThreshold(normalizeQualificationThreshold(parsed));
    setQualificationThreshold(normalized);
  };

  const handleImportAndProcess = async () => {
    if (rows.length === 0) return;
    setProcessing(true);
    try {
      // Map CSV rows to PQL records
      const pqlRows = rows.map((row) => {
        // Normalize usage score across different possible header labels
        const usageRaw =
          (row as any).product_usage_score ??
          (row as any).usage_score ??
          (row as any).score ??
          (row as any)['Usage Score (1-10)'] ??
          (row as any)['Usage Score'] ??
          null;

        const usageNum =
          usageRaw !== null && usageRaw !== undefined && usageRaw !== ''
            ? Number(usageRaw)
            : null;

        return {
          email: (row as any).email || (row as any).Email || '',
          company_name:
            (row as any).company_name ||
            (row as any).Company ||
            (row as any).company ||
            (row as any)['Company Name'] ||
            (row as any)['Company name'] ||
            null,
          product_usage_score: usageNum,
          // Only send values that are already in a date-like field.
          // Free-text values like "2 hours ago" stay in raw_data
          // (e.g. under the "Last Active" header) and are interpreted
          // later by the qualification agent.
          last_active_date:
            (row as any).last_active_date ??
            (row as any).last_active ??
            null,
          raw_data: row as any,
          status: 'pending' as const,
        };
      });

      const inserted = await insertPqls.mutateAsync(pqlRows);
      await runAgentsEnrichment(inserted);

      setRows([]);
      setHeaders([]);
      setFileName('');
    } finally {
      setProcessing(false);
    }
  };

  const handleSingleTestSubmit = async () => {
    if (!singleEmail || !singleUsage) {
      toast({
        title: 'Missing fields',
        description: 'Email and Usage Score are required for a test PQL.',
        variant: 'destructive',
      });
      return;
    }

    setProcessing(true);
    try {
      const rawRow: ParsedRow = {
        ID: singleId,
        Email: singleEmail,
        'Company Name': singleCompany,
        'Usage Score (1-10)': singleUsage,
      };

      const pqlRows = [
        {
          email: singleEmail,
          company_name: singleCompany || null,
          product_usage_score: Number(singleUsage) || null,
          last_active_date: null,
          raw_data: rawRow as any,
          status: 'pending' as const,
        },
      ];

      const inserted = await insertPqls.mutateAsync(pqlRows as any);
      await runAgentsEnrichment(inserted);

      setSingleId('');
      setSingleEmail('');
      setSingleCompany('');
      setSingleUsage('');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <div className="flex items-end gap-3">
          <div className="space-y-1">
            <Label className="text-xs">Qualification Threshold (1-10)</Label>
            <Input
              className="w-36"
              type="number"
              min={1}
              max={10}
              step={1}
              value={qualificationThreshold}
              onChange={(e) => handleThresholdChange(e.target.value)}
            />
          </div>
          <Button variant="outline" size="sm" onClick={handleTestAgentsApi}>
            Test Agents API
          </Button>
        </div>
      </div>

      {/* Upload Zone */}
      <Card className="border-2 border-dashed border-border shadow-none">
        <CardContent className="p-0">
          <label
            className="flex flex-col items-center justify-center py-16 cursor-pointer hover:bg-accent/50 transition-colors rounded-lg"
            onDragOver={(e) => e.preventDefault()}
            onDrop={onDrop}
          >
            <Upload className="h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-sm font-medium">Drop a CSV file here or click to browse</p>
            <p className="text-xs text-muted-foreground mt-1">Supports .csv files with labeled columns</p>
            <input type="file" accept=".csv" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
          </label>
        </CardContent>
      </Card>

      {/* Single test PQL form */}
      <Card className="border-0 shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm">Single Test PQL</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <Label className="text-xs">ID (optional)</Label>
              <Input
                value={singleId}
                onChange={(e) => setSingleId(e.target.value)}
                placeholder="test-1"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Email</Label>
              <Input
                value={singleEmail}
                onChange={(e) => setSingleEmail(e.target.value)}
                placeholder="user@example.com"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Company Name</Label>
              <Input
                value={singleCompany}
                onChange={(e) => setSingleCompany(e.target.value)}
                placeholder="Acme Corp"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Usage Score (1–10)</Label>
              <Input
                value={singleUsage}
                onChange={(e) => setSingleUsage(e.target.value)}
                placeholder="8"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <Button size="sm" onClick={handleSingleTestSubmit} disabled={processing}>
              {processing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {processing ? 'Processing…' : 'Submit Single Test'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Preview */}
      {rows.length > 0 && (
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4" />
                {fileName} — {rows.length} rows
              </CardTitle>
              <Button onClick={handleImportAndProcess} disabled={processing}>
                {processing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {processing ? 'Processing…' : 'Import & Process PQLs'}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="max-h-[400px] overflow-auto rounded border">
              <Table>
                <TableHeader>
                  <TableRow>
                    {headers.map((h) => <TableHead key={h}>{h}</TableHead>)}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.slice(0, 50).map((row, i) => (
                    <TableRow key={i}>
                      {headers.map((h) => <TableCell key={h}>{row[h]}</TableCell>)}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
            {rows.length > 50 && <p className="text-xs text-muted-foreground mt-2">Showing first 50 of {rows.length} rows</p>}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
