#!/home/james/stacklabs/.venv/bin/python3
"""
WO0011251 Artifact 5:
1. Updates apps/faas/src/components/battlestation/panels/IntelligencePanel.tsx so outer and inner containers bind cleanly
   to var(--bg-canvas), var(--bg-card), var(--border-card), and var(--text-primary) in Deep Void (#0B0D13).
2. Replaces apps/faas/src/components/BroadcastSearchModal.tsx to eliminate hardcoded '10052026' and
   initialQuery = 'giants', adding dynamic date selection ('latest' / '2026-10-19' default), client-side
   transcript line deduplication, and dynamic /api/lookbook/latest.pdf linkage.
"""
import os
from pathlib import Path

BASE_DIR = Path("/home/james/stacklabs")
INTEL_PANEL_CANDIDATES = [
    BASE_DIR / "apps" / "faas" / "src" / "components" / "battlestation" / "panels" / "IntelligencePanel.tsx",
    BASE_DIR / "apps" / "faas" / "src" / "components" / "IntelligencePanel.tsx",
]
SEARCH_MODAL = BASE_DIR / "apps" / "faas" / "src" / "components" / "BroadcastSearchModal.tsx"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def patch_intelligence_panel() -> None:
    for p in INTEL_PANEL_CANDIDATES:
        if p.exists():
            src = p.read_text(encoding="utf-8")
            updated = src.replace("bg-[#0E111A]", "bg-[var(--bg-canvas)] text-[var(--text-primary)]")
            updated = updated.replace("bg-[#12151F]", "bg-[var(--bg-card)] text-[var(--text-primary)]")
            updated = updated.replace("bg-[#11141E]", "bg-[var(--bg-card)] text-[var(--text-primary)]")
            updated = updated.replace("border-white/5", "border-[var(--border-card)]")
            updated = updated.replace("border-white/10", "border-[var(--border-card)]")
            if updated != src:
                atomic_write(p, updated)
                print(f"Patched {p} to use canonical CSS variables.")


BROADCAST_SEARCH_MODAL_TSX = """import React, { useState, useEffect, useCallback } from 'react';
import { Search, X, Radio, FileText, ExternalLink, Clock, Sparkles } from 'lucide-react';

interface BroadcastHit {
  timestamp?: string;
  timecode?: string;
  speaker?: string;
  text?: string;
  quote?: string;
  show?: string;
  date?: string;
  score?: number;
}

export interface BroadcastSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialQuery?: string;
  defaultShow?: string;
  initialShow?: 'mcafee' | 'horizon' | string;
}

const QUICK_SUGGESTIONS = [
  'Chris Ballard',
  'Jalen Hurts',
  'Blake Grupe',
  'Brian Schottenheimer',
  'Substation',
  'Jayden Daniels',
  'Dan Orlovsky',
];

export const BroadcastSearchModal: React.FC<BroadcastSearchModalProps> = ({
  isOpen,
  onClose,
  initialQuery = '',
  defaultShow = 'mcafee',
  initialShow,
}) => {
  const [query, setQuery] = useState<string>(initialQuery);
  const [targetShow, setTargetShow] = useState<string>(initialShow || defaultShow);
  const [targetDate, setTargetDate] = useState<string>('latest');
  const [results, setResults] = useState<BroadcastHit[]>([]);
  const [summary, setSummary] = useState<string>('');
  const [resolvedDate, setResolvedDate] = useState<string>('2026-10-19');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const executeSearch = useCallback(
    async (searchTerm: string, showSlug: string, dateFilter: string) => {
      const trimmed = searchTerm.trim();
      if (!trimmed) {
        setResults([]);
        setSummary('');
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({
          q: trimmed,
          show: showSlug,
        });
        if (dateFilter && dateFilter !== 'latest' && dateFilter !== 'all') {
          params.set('date', dateFilter);
        }
        const url = `/api/broadcast/query?${params.toString()}`;
        const res = await fetch(url);
        if (!res.ok) {
          throw new Error(`Broadcast search returned HTTP ${res.status}`);
        }
        const data = await res.json();
        let rawHits: BroadcastHit[] = Array.isArray(data.results)
          ? data.results
          : Array.isArray(data.hits)
          ? data.hits
          : Array.isArray(data.matches)
          ? data.matches
          : [];

        if (rawHits.length === 0 && Array.isArray(data.file_matches)) {
          for (const fm of data.file_matches) {
            if (Array.isArray(fm.matches)) {
              for (const pair of fm.matches) {
                if (Array.isArray(pair) && pair.length >= 2) {
                  rawHits.push({
                    timestamp: String(pair[0]),
                    text: String(pair[1]),
                    speaker: `PAT MCAFEE SHOW • ${fm.file || 'TRANSCRIPT'}`,
                  });
                }
              }
            }
          }
        }

        const seen = new Set<string>();
        const deduped: BroadcastHit[] = [];
        for (const item of rawHits) {
          const body = (item.text || item.quote || '').trim();
          const ts = (item.timestamp || item.timecode || '').trim();
          const key = `${ts}::${body.toLowerCase()}`;
          if (body && !seen.has(key)) {
            seen.add(key);
            deduped.push(item);
          }
        }

        setResults(deduped);
        setSummary(data.summary || data.synthesis || data.summary_description || '');
        if (data.date || data.resolved_date) {
          setResolvedDate(String(data.date || data.resolved_date));
        }
      } catch (err: any) {
        setError(err?.message || 'Failed to query broadcast intelligence');
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    if (isOpen && initialQuery.trim()) {
      setQuery(initialQuery);
      executeSearch(initialQuery, targetShow, targetDate);
    }
  }, [isOpen, initialQuery, targetShow, targetDate, executeSearch]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-4xl rounded-lg bg-[var(--bg-card)] border border-[var(--border-card)] text-[var(--text-primary)] shadow-2xl overflow-hidden flex flex-col max-h-[88vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-[var(--bg-canvas)] border-b border-[var(--border-card)]">
          <div className="flex items-center gap-2.5">
            <Radio className="w-4 h-4 text-emerald-400 animate-pulse"/>
            <span className="font-mono text-xs uppercase tracking-wider font-semibold text-[var(--text-primary)]">
              BROADCAST WIRE SEARCH • ARTEMIS CUDA TRANSCRIPT VAULT ({resolvedDate})
            </span>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="/api/lookbook/latest.pdf"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20 transition-colors"
            >
              <FileText className="w-3.5 h-3.5"/>
              LATEST LOOKBOOK PDF
              <ExternalLink className="w-3 h-3"/>
            </a>
            <button
              onClick={onClose}
              className="p-1 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/5"
              aria-label="Close modal"
            >
              <X className="w-4 h-4"/>
            </button>
          </div>
        </div>

        {/* Search Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            executeSearch(query, targetShow, targetDate);
          }}
          className="p-4 bg-[var(--bg-surface)] border-b border-[var(--border-card)] flex flex-col gap-3"
        >
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-[var(--text-secondary)] absolute left-3.5 top-1/2 -translate-y-1/2"/>
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search today's October 19 McAfee tape (e.g., Ballard, Hurts blood clot, Grupe, Substation, Orlovsky)..."
                className="w-full pl-10 pr-4 py-2.5 rounded bg-[var(--bg-canvas)] border border-[var(--border-card)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-emerald-500/50 font-mono"
                autoFocus
              />
            </div>
            <select
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              className="px-3 py-2.5 rounded bg-[var(--bg-canvas)] border border-[var(--border-card)] text-xs font-mono text-[var(--text-primary)]"
            >
              <option value="latest">LATEST (OCT 19, 2026)</option>
              <option value="10192026">2026-10-19 (LEVI'S STADIUM)</option>
              <option value="all">ALL ARCHIVED TAPES</option>
            </select>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2.5 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-xs font-mono font-semibold uppercase tracking-wider text-white transition-colors"
            >
              {loading ? 'SCANNING...' : 'SNIPE'}
            </button>
          </div>

          {/* Quick Suggested Entities from Today's Tape */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] font-mono uppercase tracking-wider text-[var(--text-muted)] mr-1">
              OCT 19 HOT TAGS:
            </span>
            {QUICK_SUGGESTIONS.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => {
                  setQuery(tag);
                  executeSearch(tag, targetShow, targetDate);
                }}
                className="px-2 py-0.5 rounded text-[11px] font-mono bg-[var(--bg-canvas)] border border-[var(--border-card)] text-[var(--text-secondary)] hover:text-emerald-300 hover:border-emerald-500/40 transition-colors"
              >
                {tag}
              </button>
            ))}
          </div>
        </form>

        {/* Results Pane */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-[var(--bg-canvas)]">
          {error && (
            <div className="p-3 rounded bg-red-500/10 border border-red-500/30 text-red-300 text-xs font-mono">
              {error}
            </div>
          )}

          {summary && (
            <div className="p-3.5 rounded bg-[var(--bg-card)] border border-emerald-500/30">
              <div className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-400 uppercase mb-1">
                <Sparkles className="w-3.5 h-3.5"/>
                SYNTHESIZED INTEL BRIEF
              </div>
              <p className="text-xs leading-relaxed text-[var(--text-primary)]">{summary}</p>
            </div>
          )}

          {!loading && results.length === 0 && query.trim() !== '' && !error && (
            <div className="text-center py-10 text-xs font-mono text-[var(--text-muted)]">
              ZERO TRANSCRIPT HITS FOR "{query.toUpperCase()}" IN SELECTED WINDOW.
            </div>
          )}

          {!loading && query.trim() === '' && (
            <div className="text-center py-10 text-xs font-mono text-[var(--text-secondary)]">
              SELECT AN OCT 19 HOT TAG ABOVE OR ENTER ANY PLAYER, COACH, OR TOPIC TO SCAN THE 3-HOUR BROADCAST VAULT.
            </div>
          )}

          <div className="space-y-2.5">
            {results.map((hit, idx) => {
              const ts = hit.timestamp || hit.timecode || 'LIVE';
              const body = hit.text || hit.quote || '';
              return (
                <div
                  key={`${ts}-${idx}`}
                  className="p-3 rounded bg-[var(--bg-card)] border border-[var(--border-card)] hover:border-emerald-500/30 transition-colors"
                >
                  <div className="flex items-center justify-between text-[11px] font-mono text-[var(--text-secondary)] mb-1">
                    <span className="inline-flex items-center gap-1 text-emerald-400">
                      <Clock className="w-3 h-3"/>
                      {ts}
                    </span>
                    <span>{hit.speaker || 'PAT MCAFEE SHOW • LEVI STADIUM'}</span>
                  </div>
                  <p className="text-xs leading-relaxed text-[var(--text-primary)]">{body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BroadcastSearchModal;
"""


if __name__ == "__main__":
    patch_intelligence_panel()
    atomic_write(SEARCH_MODAL, BROADCAST_SEARCH_MODAL_TSX)
    print("Updated BroadcastSearchModal.tsx with dynamic date resolution and line deduplication.")
