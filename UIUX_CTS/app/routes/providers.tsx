import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { AppShell, PageHeader, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { SAFETY_NOTE, type CareType } from "@/lib/mock-data";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

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

// ── Mock providers ──
const MOCK_PROVIDERS = [
  { NPI: "1234567890", Name: "Riverbend Family Medicine", Specialty: "Family Medicine", CareType: "Primary Care", Norm_Quality: 0.92 },
  { NPI: "0987654321", Name: "Northside Community Health", Specialty: "Internal Medicine", CareType: "Primary Care", Norm_Quality: 0.88 },
  { NPI: "1122334455", Name: "Springfield Primary Partners", Specialty: "Family Medicine", CareType: "Primary Care", Norm_Quality: 0.85 },
  { NPI: "2233445566", Name: "Cedar Street Urgent Care", Specialty: "Urgent Care", CareType: "Urgent Care", Norm_Quality: 0.90 },
  { NPI: "3344556677", Name: "Westgate Urgent Care", Specialty: "Urgent Care", CareType: "Urgent Care", Norm_Quality: 0.87 },
  { NPI: "4455667788", Name: "QuickCare Walk-In Clinic", Specialty: "Urgent Care", CareType: "Urgent Care", Norm_Quality: 0.83 },
  { NPI: "5566778899", Name: "CarePath Virtual Clinic", Specialty: "Telehealth", CareType: "Telehealth", Norm_Quality: 0.91 },
  { NPI: "6677889900", Name: "Nurse Line — 24/7 Advice", Specialty: "Telehealth", CareType: "Telehealth", Norm_Quality: 0.89 },
  { NPI: "7788990011", Name: "HealthBridge Telehealth", Specialty: "Telehealth", CareType: "Telehealth", Norm_Quality: 0.86 },
  { NPI: "8899001122", Name: "Population Health Care Team", Specialty: "Care Management", CareType: "Care Management", Norm_Quality: 0.94 },
  { NPI: "9900112233", Name: "Chronic Care Navigators", Specialty: "Care Management", CareType: "Care Management", Norm_Quality: 0.88 },
  { NPI: "0011223344", Name: "Community Health Workers", Specialty: "Care Management", CareType: "Care Management", Norm_Quality: 0.82 },
];

function ProvidersPage() {
  const { care = "All" } = Route.useSearch();
  const [page, setPage] = useState(1);
  const limit = 10;

  const filteredProviders = care === "All" ? MOCK_PROVIDERS : MOCK_PROVIDERS.filter(p => p.CareType === care);
  const total = filteredProviders.length;
  const totalPages = Math.ceil(total / limit);
  const paginatedProviders = filteredProviders.slice((page - 1) * limit, page * limit);

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
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
              <th className="px-5 py-3.5 font-medium">Provider</th>
              <th className="px-5 py-3.5 font-medium">Specialty</th>
              <th className="hidden px-5 py-3.5 font-medium md:table-cell">NPI</th>
              <th className="px-5 py-3.5 font-medium">Quality Score</th>
              <th className="hidden px-5 py-3.5 font-medium sm:table-cell">Availability</th>
            </tr>
          </thead>
          <tbody>
            {paginatedProviders.length > 0 ? paginatedProviders.map((p) => (
              <tr key={p.NPI} className="border-b border-border last:border-0 hover:bg-muted/40">
                <td className="px-5 py-5 font-medium text-foreground">{p.Name}</td>
                <td className="px-5 py-5 text-muted-foreground">{p.Specialty}</td>
                <td className="hidden px-5 py-5 text-muted-foreground md:table-cell font-mono text-xs">{p.NPI}</td>
                <td className="px-5 py-5 tabular-nums text-muted-foreground">{p.Norm_Quality}</td>
                <td className="hidden px-5 py-5 text-muted-foreground sm:table-cell">
                  <span className="inline-flex items-center rounded-full border border-green-200 bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
                    Available
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
        
        {totalPages > 1 && (
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
