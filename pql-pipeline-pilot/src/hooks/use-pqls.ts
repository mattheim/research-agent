import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { toast } from '@/hooks/use-toast';
import type { Tables, TablesInsert } from '@/integrations/supabase/types';

export type Pql = Tables<'pqls'>;
export type Enrichment = Tables<'enrichments'>;
export type EmailDraft = Tables<'email_drafts'>;

export function usePqls() {
  return useQuery({
    queryKey: ['pqls'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('pqls')
        .select('*')
        .order('created_at', { ascending: false });
      if (error) throw error;
      return data;
    },
  });
}

export function usePqlDetail(id: string | null) {
  return useQuery({
    queryKey: ['pql', id],
    enabled: !!id,
    queryFn: async () => {
      const [pqlRes, enrichRes, draftRes] = await Promise.all([
        supabase.from('pqls').select('*').eq('id', id!).single(),
        supabase.from('enrichments').select('*').eq('pql_id', id!).maybeSingle(),
        supabase.from('email_drafts').select('*').eq('pql_id', id!).maybeSingle(),
      ]);
      if (pqlRes.error) throw pqlRes.error;
      return {
        pql: pqlRes.data,
        enrichment: enrichRes.data,
        emailDraft: draftRes.data,
      };
    },
  });
}

export function useInsertPqls() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (rows: TablesInsert<'pqls'>[]) => {
      const { data, error } = await supabase.from('pqls').insert(rows).select();
      if (error) throw error;
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pqls'] });
      toast({ title: 'PQLs imported successfully' });
    },
    onError: (e) => toast({ title: 'Import failed', description: e.message, variant: 'destructive' }),
  });
}

export function useUpdatePqlStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const { error } = await supabase.from('pqls').update({ status }).eq('id', id);
      if (error) throw error;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pqls'] }),
  });
}

export function useUpdateEmailDraft() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, subject, body, proposed_offer }: { id: string; subject: string; body: string; proposed_offer?: string }) => {
      const { error } = await supabase.from('email_drafts').update({ subject, body, proposed_offer, is_edited: true }).eq('id', id);
      if (error) throw error;
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ['pql'] });
    },
  });
}

export function useLogActivity() {
  return useMutation({
    mutationFn: async ({ pql_id, action, details }: { pql_id?: string; action: string; details?: Record<string, unknown> }) => {
      const { error } = await supabase.from('activity_log').insert({ pql_id, action, details: details as any });
      if (error) throw error;
    },
  });
}

export function useDeletePql() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.from('pqls').delete().eq('id', id);
      if (error) throw error;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pqls'] });
      toast({ title: 'PQL deleted' });
    },
    onError: (e) =>
      toast({
        title: 'Delete failed',
        description: e.message,
        variant: 'destructive',
      }),
  });
}
