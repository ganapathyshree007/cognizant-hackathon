import { createFileRoute } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { AppShell, PageHeader, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { SAFETY_NOTE, type CareType } from "@/lib/mock-data";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useAuth } from "./__root";
import { apiUrl } from "@/lib/api";

type ProviderSearch = { care?: CareType | "All" };

const careTypes: (CareType | "All")[] = [
  "All",
  "Primary Care",
  "Urgent Care",
  "Telehealth",
  "Care Management",
];

export const Route = createFileRoute("/providers")({
  validateSearch: (search: Record<string, unknown>): ProviderSearch => {
    const care = search["care"];
    return typeof care === "string" && careTypes.includes(care as CareType)
      ? { care: care as CareType }
      : {};
  },
  head: () => ({
    meta: [
      { title: "Care options — CarePath Care Navigation" },
    ],
  }),
  component: ProvidersPage,
});

function ProvidersPage() {
  const { care = "All" } = Route.useSearch();
  const { session } = useAuth();
  const [providers, setProviders] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const limit = 10;

  useEffect(() => {
    setPage(1);
  }, [care]);

  useEffect(() => {
    const fetchProviders = async () => {
      setLoading(true);
      try {
        const token = session?.access_token || "mock-token-123";
        const response = await fetch(apiUrl(`/api/providers?page=${page}&limit=${limit}&care=${encodeURIComponent(care)}`), {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
          const text = await response.text();
          const res = text ? JSON.parse(text) : {};
          setProviders(res.data || []);
          setTotal(res.total || 0);
        }
      } catch (e) {
        console.error("Failed to fetch providers:", e);
      } finally {
        setLoading(false);
      }
    };
    fetchProviders();
  }, [care, page, session]);

  const totalPages = Math.ceil(total / limit);

  return (
    <AppShell>
      <Breadcrumbs items={[
        { label: "Dashboard", to: "/" },
        { label: "Providers" },
      ]} />
      <PageHeader
        title="Providers"
        subtitle="Alternative care options available to patients in the service area."
      />

      <div className="mb-6 flex flex-wrap gap-1.5">
        {careTypes.map((t) => (
          <a
            key={t}
            href={t === "All" ? "/providers" : `/providers?care=${encodeURIComponent(t)}`}
            className={cn(
              "rounded-full border px-3 py-1 text-xs transition-colors",
              care === t
                ? "border-primary/30 bg-primary/10 text-primary font-medium"
                : "border-border text-muted-foreground hover:bg-muted"
            )}
          >
            {t}
          </a>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        {loading ? (
          <div className="p-8 text-center text-muted-foreground animate-pulse">Loading provider directory...</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground bg-muted/20">
                <th className="px-5 py-3.5 font-medium">Provider Name</th>
                <th className="px-5 py-3.5 font-medium">Specialty</th>
                <th className="hidden px-5 py-3.5 font-medium md:table-cell">NPI / PAC ID</th>
                <th className="px-5 py-3.5 font-medium">Quality Score</th>
                <th className="hidden px-5 py-3.5 font-medium sm:table-cell">Availability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {providers.length > 0 ? providers.map((p, idx) => (
                <tr key={p.NPI || p.PAC_ID || idx} className="hover:bg-muted/40 transition-colors">
                  <td className="px-5 py-4 font-medium text-foreground">{p.Name}</td>
                  <td className="px-5 py-4 text-muted-foreground">{p.Specialty}</td>
                  <td className="hidden px-5 py-4 text-muted-foreground md:table-cell font-mono text-xs">{p.NPI || p.PAC_ID || "—"}</td>
                  <td className="px-5 py-4 tabular-nums text-muted-foreground font-medium">{p.Norm_Quality ?? "—"}</td>
                  <td className="hidden px-5 py-4 text-muted-foreground sm:table-cell">
                    <span className="inline-flex items-center rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                      In-Network
                    </span>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-muted-foreground">No providers found for this category.</td>
                </tr>
              )}
            </tbody>
          </table>
        )}
        
        {!loading && totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-border px-5 py-3">
            <span className="text-xs text-muted-foreground">
              Showing {(page - 1) * limit + 1} to {Math.min(page * limit, total)} of {total} providers
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="w-4 h-4 mr-1" /> Prev
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
              >
                Next <ChevronRight className="w-4 h-4 ml-1" />
              </Button>
            </div>
          </div>
        )}
      </div>

      <div className="mt-8">
        <SafetyNote text={SAFETY_NOTE} />
      </div>
    </AppShell>
  );
}
