export const PQL_STATUSES = {
  pending: { label: 'Potential', color: 'bg-warning text-warning-foreground' },
  qualified: { label: 'Qualified', color: 'bg-success text-success-foreground' },
  sent: { label: 'Sent', color: 'bg-primary text-primary-foreground' },
  // Not ready: red text/icon only, no background pill
  rejected: { label: 'Not Ready', color: 'text-destructive' },
} as const;

export type PqlStatus = keyof typeof PQL_STATUSES;

// Update this to your local agents API base URL
export const AGENTS_API_BASE_URL = 'http://localhost:8000';

export const DEFAULT_QUALIFICATION_THRESHOLD = 8;
export const QUALIFICATION_THRESHOLD_STORAGE_KEY = 'qualification_threshold';

export function normalizeQualificationThreshold(value: number): number {
  if (!Number.isFinite(value)) return DEFAULT_QUALIFICATION_THRESHOLD;
  return Math.min(10, Math.max(1, Math.round(value)));
}

export function getStoredQualificationThreshold(): number {
  if (typeof window === 'undefined') return DEFAULT_QUALIFICATION_THRESHOLD;
  const raw = window.localStorage.getItem(QUALIFICATION_THRESHOLD_STORAGE_KEY);
  if (!raw) return DEFAULT_QUALIFICATION_THRESHOLD;
  return normalizeQualificationThreshold(Number(raw));
}

export function setStoredQualificationThreshold(value: number): number {
  const normalized = normalizeQualificationThreshold(value);
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(QUALIFICATION_THRESHOLD_STORAGE_KEY, String(normalized));
  }
  return normalized;
}
