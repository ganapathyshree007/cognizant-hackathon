import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Search, ChevronRight } from "lucide-react";
import { AppShell, PageHeader, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getPatientName } from "@/lib/utils";

export const Route = createFileRoute("/patients/")({
  head: () => ({
    meta: [
      { title: "All Patients — CarePath Care Navigation" },
      {
        name: "description",
        content: "Search and review patient history for care navigation.",
      },
    ],
  }),
  component: PatientsPage,
});

function PatientsPage() {
  const [searchInput, setSearchInput] = useState("");
  const [patients, setPatients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    async function loadPatients() {
      setLoading(true);
      try {
        const res = await fetch(`/api/patients/search?query=${searchInput.trim()}`);
        if (!res.ok) throw new Error("Backend search failed");
        const data = await res.json();

        const mapped = (data || []).map((p: any) => {
          const name = getPatientName(p.PATIENT_ID, p.gender);
          const risk = p.target_repeat_ed_90d > 0 ? "HIGH" : "MEDIUM";
          return {
            PATIENT_ID: p.PATIENT_ID,
            NAME: name,
            AGE: Math.round(p.age_at_index || 45),
            ED_VISITS: p.target_repeat_ed_90d || 0,
            RISK: risk,
            ENCOUNTER_ID: p.ENCOUNTER_ID
          };
        });
        setPatients(mapped);
      } catch (err) {
        console.error("Error loading patients:", err);
      } finally {
        setLoading(false);
      }
    }

    const handler = setTimeout(() => {
      loadPatients();
    }, 300);

    return () => clearTimeout(handler);
  }, [searchInput]);

  return (
    <AppShell>
      <Breadcrumbs items={[
        { label: "Dashboard", to: "/" },
        { label: "Patients" },
      ]} />
      <PageHeader
        title="All Patients & Encounters"
        subtitle="Search patient history to run the clinical orchestration workflow."
      />

      <div className="mb-6 bg-card p-5 rounded-xl shadow-sm border border-border">
        <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <Search className="w-4 h-4" /> Search Patient History
        </h2>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by Patient ID..."
            className="flex-1"
          />
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground bg-muted/20">
              <th className="px-5 py-3.5 font-medium">Patient ID</th>
              <th className="px-5 py-3.5 font-medium">Patient Name</th>
              <th className="px-5 py-3.5 font-medium">Age</th>
              <th className="px-5 py-3.5 font-medium">ED Visits (6mo)</th>
              <th className="px-5 py-3.5 font-medium">Risk Level</th>
              <th className="px-5 py-3.5 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-5 py-12 text-center text-sm text-muted-foreground animate-pulse">
                  Loading patients from database...
                </td>
              </tr>
            ) : (
              patients.map((r, i) => (
                <tr key={i} className="hover:bg-muted/40 transition-colors">
                  <td className="px-5 py-3.5 whitespace-nowrap font-mono text-xs text-muted-foreground">
                    {r.PATIENT_ID}
                  </td>
                  <td className="px-5 py-3.5 whitespace-nowrap font-medium text-foreground">
                    {r.NAME}
                  </td>
                  <td className="px-5 py-3.5 whitespace-nowrap text-muted-foreground">
                    {r.AGE}
                  </td>
                  <td className="px-5 py-3.5 whitespace-nowrap font-medium">
                    {r.ED_VISITS}
                  </td>
                  <td className="px-5 py-3.5 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      r.RISK === "HIGH" ? "bg-destructive/10 text-destructive" :
                      r.RISK === "MEDIUM" ? "bg-amber-100 text-amber-700" :
                      "bg-green-100 text-green-700"
                    }`}>
                      {r.RISK}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 whitespace-nowrap font-medium text-right">
                    <Button
                      variant="outline"
                      size="sm"
                      className="gap-1"
                      onClick={() => {
                        navigate({
                          to: `/patients/${r.PATIENT_ID}`,
                          search: { encounterId: r.ENCOUNTER_ID },
                        });
                      }}
                    >
                      View <ChevronRight className="w-3.5 h-3.5" />
                    </Button>
                  </td>
                </tr>
              ))
            )}
            {!loading && patients.length === 0 && (
              <tr>
                <td colSpan={6} className="px-5 py-12 text-center text-sm text-muted-foreground">
                  No patients match this search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-8">
        <SafetyNote text="Patient data shown is from synthetic CMS datasets. This list identifies care navigation opportunities, not judgments about individual visits." />
      </div>
    </AppShell>
  );
}
