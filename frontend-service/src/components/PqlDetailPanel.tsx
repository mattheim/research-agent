import { useState, useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { StatusBadge } from '@/components/StatusBadge';
import { usePqlDetail, useUpdatePqlStatus, useUpdateEmailDraft, useLogActivity, useDeletePql } from '@/hooks/use-pqls';
import { supabase } from '@/integrations/supabase/client';
import { toast } from '@/hooks/use-toast';
import { Send, XCircle, Building2, Users, Sparkles, Trash2 } from 'lucide-react';
import { AGENTS_API_BASE_URL, getStoredQualificationThreshold } from '@/lib/constants';

interface PqlDetailPanelProps {
  pqlId: string;
  onClose: () => void;
}

export function PqlDetailPanel({ pqlId, onClose }: PqlDetailPanelProps) {
  const { data, isLoading } = usePqlDetail(pqlId);
  const updateStatus = useUpdatePqlStatus();
  const updateDraft = useUpdateEmailDraft();
  const logActivity = useLogActivity();
  const deletePql = useDeletePql();
  const queryClient = useQueryClient();

  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [proposedOffer, setProposedOffer] = useState('');
  const [sending, setSending] = useState(false);
  const [enriching, setEnriching] = useState(false);

  useEffect(() => {
    if (data?.emailDraft) {
      setSubject(data.emailDraft.subject);
      setBody(data.emailDraft.body);
      setProposedOffer(data.emailDraft.proposed_offer ?? '');
    }
  }, [data?.emailDraft]);

  if (isLoading) return <div className="p-8 text-center text-muted-foreground">Loading…</div>;
  if (!data) return null;

  const { pql, enrichment, emailDraft } = data;

  const handleRerunEnrichment = async () => {
    setEnriching(true);
    try {
      const resp = await fetch(`${AGENTS_API_BASE_URL}/pqls/${pqlId}/enrich`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          qualification_threshold: getStoredQualificationThreshold(),
        }),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || `Status ${resp.status}`);
      }
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['pql', pqlId] }),
        queryClient.invalidateQueries({ queryKey: ['pqls'] }),
      ]);
      toast({ title: 'Enrichment refreshed' });
    } catch (e: any) {
      toast({
        title: 'Failed to re-run enrichment',
        description: e.message,
        variant: 'destructive',
      });
    } finally {
      setEnriching(false);
    }
  };

  const handleApproveAndSend = async () => {
    if (!emailDraft) return;
    setSending(true);
    try {
      // Save any edits first
      if (
        subject !== emailDraft.subject ||
        body !== emailDraft.body ||
        proposedOffer !== (emailDraft.proposed_offer ?? '')
      ) {
        await updateDraft.mutateAsync({
          id: emailDraft.id,
          subject,
          body,
          proposed_offer: proposedOffer,
        });
      }

      // Call send-email edge function
      const { error } = await supabase.functions.invoke('send-email', {
        // Omit custom "from" so the edge function can use a verified
        // default sender (e.g. onboarding@resend.dev) or your configured domain.
        body: { to: emailDraft.to_email, subject, body },
      });

      if (error) throw error;

      await updateStatus.mutateAsync({ id: pqlId, status: 'sent' });
      await logActivity.mutateAsync({
        pql_id: pqlId,
        action: 'email_sent',
        details: { to: emailDraft.to_email, subject, proposed_offer: proposedOffer },
      });
      toast({ title: 'Email sent successfully!' });
      onClose();
    } catch (e: any) {
      toast({ title: 'Failed to send', description: e.message, variant: 'destructive' });
    } finally {
      setSending(false);
    }
  };

  const handleReject = async () => {
    const now = new Date().toISOString();
    const existingMeta =
      pql.agent_metadata && typeof pql.agent_metadata === 'object'
        ? (pql.agent_metadata as Record<string, unknown>)
        : {};
    const existingTags = Array.isArray(existingMeta.human_tags)
      ? existingMeta.human_tags.map(String)
      : [];
    const nextTags = Array.from(new Set([...existingTags, 'not_ready']));

    const { error } = await supabase
      .from('pqls')
      .update({
        status: 'rejected',
        agent_metadata: {
          ...existingMeta,
          human_tags: nextTags,
          rejection_label: 'not_ready',
          rejected_at: now,
        },
      })
      .eq('id', pqlId);
    if (error) {
      toast({ title: 'Failed to reject lead', description: error.message, variant: 'destructive' });
      return;
    }

    await logActivity.mutateAsync({
      pql_id: pqlId,
      action: 'rejected',
      details: { tag: 'not_ready', tagged_at: now },
    });
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['pql', pqlId] }),
      queryClient.invalidateQueries({ queryKey: ['pqls'] }),
    ]);
    toast({ title: 'Marked as Not Ready' });
    onClose();
  };

  const handleDelete = async () => {
    try {
      await deletePql.mutateAsync(pqlId);
      onClose();
    } catch (e: any) {
      toast({ title: 'Delete failed', description: e.message, variant: 'destructive' });
    }
  };

  const companyInfo = enrichment?.company_info as Record<string, unknown> | null;
  const keyContacts = enrichment?.key_contacts as Array<Record<string, unknown>> | null;
  const raw = (pql.raw_data || {}) as Record<string, any>;
  const companyDisplay =
    pql.company_name ||
    raw['Company Name'] ||
    raw['Company name'] ||
    raw.Company ||
    raw.company_name ||
    raw.company ||
    pql.email;
  const agentMeta = (pql.agent_metadata || {}) as Record<string, any>;
  const qualificationReasoning = agentMeta.ai_reasoning as string | undefined;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">{companyDisplay}</h2>
          <StatusBadge status={pql.status} />
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRerunEnrichment}
            disabled={enriching}
          >
            <Sparkles className="mr-1 h-3.5 w-3.5" />
            {enriching ? 'Refreshing…' : 'Re-run enrichment'}
          </Button>
          <Button variant="ghost" size="sm" onClick={onClose}>✕</Button>
        </div>
      </div>

      {/* Enrichment Info */}
      {enrichment && (
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-1.5"><Building2 className="h-4 w-4" /> Company Info</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-1">
            {companyInfo && Object.entries(companyInfo).map(([k, v]) => (
              <div key={k}><span className="font-medium capitalize">{k.replace(/_/g, ' ')}:</span> {String(v)}</div>
            ))}
          </CardContent>
        </Card>
      )}

      {keyContacts && keyContacts.length > 0 && (
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-1.5"><Users className="h-4 w-4" /> Key Contacts</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-1">
            {keyContacts.map((c, i) => (
              <div key={i}>{String(c.name ?? '')} — {String(c.title ?? '')} ({String(c.email ?? '')})</div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Proposed Offer Editor */}
      {emailDraft && (
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-1.5">
              <Sparkles className="h-4 w-4" /> Proposed Offer
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Textarea
              value={proposedOffer}
              onChange={(e) => setProposedOffer(e.target.value)}
              className="min-h-[110px]"
            />
          </CardContent>
        </Card>
      )}

      {/* AI Reasoning (Qualification first, then email if present) */}
      {(qualificationReasoning || emailDraft?.ai_reasoning) && (
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-1.5"><Sparkles className="h-4 w-4" /> AI Reasoning</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground whitespace-pre-wrap">
            {qualificationReasoning || emailDraft?.ai_reasoning}
          </CardContent>
        </Card>
      )}

      {/* Email Draft Editor */}
      {emailDraft && (
        <Card className="border-0 shadow-sm">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Email Draft</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground">To</label>
              <Input value={emailDraft.to_email} disabled className="mt-1" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Subject</label>
              <Input value={subject} onChange={(e) => setSubject(e.target.value)} className="mt-1" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Body</label>
              <Textarea value={body} onChange={(e) => setBody(e.target.value)} className="mt-1 min-h-[200px]" />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        {emailDraft && pql.status === 'qualified' && (
          <Button onClick={handleApproveAndSend} disabled={sending} className="flex-1">
            <Send className="mr-2 h-4 w-4" />
            {sending ? 'Sending…' : 'Approve & Send'}
          </Button>
        )}
        {pql.status !== 'rejected' && pql.status !== 'sent' && (
          <Button variant="outline" onClick={handleReject} className="flex-1 text-destructive hover:text-destructive">
            <XCircle className="mr-2 h-4 w-4" />
            Reject
          </Button>
        )}
        <Button
          variant="outline"
          onClick={handleDelete}
          className="flex-1 text-destructive hover:text-destructive"
        >
          <Trash2 className="mr-2 h-4 w-4" />
          Delete
        </Button>
      </div>
    </div>
  );
}
