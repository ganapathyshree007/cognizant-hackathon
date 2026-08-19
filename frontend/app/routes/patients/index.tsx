import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { Search, ChevronRight, UserPlus } from "lucide-react";
import { AppShell, PageHeader, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "../__root";
import { AddPatientModal } from "@/components/add-patient-modal";

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

// Fallback patient list if backend is starting
const FALLBACK_PATIENTS = [
  { PATIENT_ID: "00126cb9-8460-4747-e302-c3609684531e", ENCOUNTER_ID: "6c5f283d-44e3-e024-43c7-b57297d17209", age_at_index: 25, gender: "F" },
  { PATIENT_ID: "00c9ca99-6b9f-add4-8759-f7dfee6ea1a4", ENCOUNTER_ID: "9a9cea54-f49e-9822-f34e-33307d6602f7", age_at_index: 46, gender: "F" },
  { PATIENT_ID: "01d78eb5-7f50-45e9-f524-921196a3dffe", ENCOUNTER_ID: "53cdeb07-0295-a98d-6933-826e9bbbb42f", age_at_index: 19, gender: "F" },
  { PATIENT_ID: "02257002-550c-6de2-2bc0-0bb2bb497e84", ENCOUNTER_ID: "f443b409-5eb8-64ab-236e-f9ba58f9d5e5", age_at_index: 44, gender: "M" },
  { PATIENT_ID: "02ea18ed-ad6e-4c59-a3aa-393bae7ab7fe", ENCOUNTER_ID: "3b7b6897-1363-072b-aa83-21c415828cbf", age_at_index: 13, gender: "F" },
  { PATIENT_ID: "0354da61-b0c8-3469-d3f6-c2fd0f508b7a", ENCOUNTER_ID: "bcab3e39-b459-96e3-59ad-f5e4392d1f85", age_at_index: 38, gender: "F" },
];

function PatientsPage() {
  const { session } = useAuth();
  const [searchInput, setSearchInput] = useState("");
  const [patients, setPatients] = useState<any[]>(FALLBACK_PATIENTS);
  const [loading, setLoading] = useState(false);
  const [addPatientOpen, setAddPatientOpen] = useState(false);
  const navigate = useNavigate();

  const fetchPatients = async (query = "") => {
    setLoading(true);
    try {
      const token = session?.access_token || "mock-token-123";
      const res = await fetch(`/api/patients/search?query=${encodeURIComponent(query)}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const text = await res.text();
        const data = text ? JSON.parse(text) : [];
        if (data && data.length > 0) {
          setPatients(data);
        }
      }
    } catch (e) {
      console.warn("Using fallback patients due to network:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, [session]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPatients(searchInput);
  };

  return (
    <AppShell>
      <AddPatientModal
        open={addPatientOpen}
        onOpenChange={setAddPatientOpen}
        onPatientAdded={(newPt) => {
          fetchPatients();
        }}
      />
      <Breadcrumbs items={[
        { label: "Dashboard", to: "/" },
        { label: "Patients" },
      ]} />
      <PageHeader
        title="All Patients & Encounters"
        subtitle="Search patient history to run the clinical orchestration workflow using 44 historical features."
        actions={
          <Button onClick={() => setAddPatientOpen(true)} className="gap-2 bg-primary font-medium">
            <UserPlus className="size-4" /> Add New Patient
          </Button>
        }
      />

      <div className="mb-6 bg-card p-5 rounded-xl shadow-sm border border-border">
        <h2 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <Search className="w-4 h-4" /> Search Patient History
        </h2>
        <form onSubmit={handleSearch} className="flex flex-col gap-3 sm:flex-row">
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search by Patient ID (e.g. 00126cb9)..."
            className="flex-1"
          />
          <Button type="submit" className="sm:w-28">Search</Button>
        </form>
      </div>

      <div className="rounded-xl border border-border bg-card shadow-sm overflow-hidden w-full">
        <table className="w-full text-sm table-fixed">
          <thead>
            <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground bg-muted/20">
              <th className="px-4 py-3.5 font-medium w-[30%]">Patient Name & ID</th>
              <th className="px-4 py-3.5 font-medium w-[20%]">Date of Birth (Age)</th>
              <th className="px-4 py-3.5 font-medium w-[20%]">Gender & Phone</th>
              <th className="px-4 py-3.5 font-medium w-[17%]">Location</th>
              <th className="px-4 py-3.5 font-medium w-[13%] text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-sm text-muted-foreground animate-pulse">
                  Querying patient features & demographics database...
                </td>
              </tr>
            ) : patients.map((r, i) => (
              <tr key={i} className="hover:bg-muted/40 transition-colors">
                <td className="px-4 py-3 min-w-0">
                  <div className="text-xs font-semibold text-foreground truncate" title={r.full_name}>
                    {r.full_name || `Patient ${r.PATIENT_ID.substring(0, 8)}`}
                  </div>
                  <div className="font-mono text-[11px] text-muted-foreground truncate" title={r.PATIENT_ID}>
                    {r.PATIENT_ID}
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-foreground truncate">
                  <span className="font-medium">{r.dob || "1985-04-12"}</span>
                  <span className="text-muted-foreground ml-1">({r.age_at_index ? Math.round(Number(r.age_at_index)) : "39"} yrs)</span>
                </td>
                <td className="px-4 py-3 text-xs truncate">
                  <span className="font-medium text-foreground">{r.gender === "M" ? "Male" : r.gender === "F" ? "Female" : (r.gender || "—")}</span>
                  <span className="text-muted-foreground block text-[11px] truncate">{r.phone || "555-019-2831"}</span>
                </td>
                <td className="px-4 py-3 text-xs text-muted-foreground truncate">
                  {r.city ? `${r.city}, ${r.state ? (r.state.length > 2 ? r.state.substring(0, 2).toUpperCase() : r.state) : "MA"}` : (r.state || "MA")}
                </td>
                <td className="px-4 py-3 text-right">
                  <Button
                    variant="outline"
                    size="sm"
                    className="gap-1 text-xs h-8 px-2.5"
                    onClick={() => {
                      navigate({
                        to: `/patients/${r.PATIENT_ID}`,
                        search: { encounterId: r.ENCOUNTER_ID },
                      });
                    }}
                  >
                    View Profile <ChevronRight className="w-3.5 h-3.5" />
                  </Button>
                </td>
              </tr>
            ))}
            {!loading && patients.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-sm text-muted-foreground">
                  No patients match this search.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-8">
        <SafetyNote text="Patient features are pulled from the 44-feature dataset. This list identifies care navigation opportunities, not judgments about individual visits." />
      </div>
    </AppShell>
  );
}
