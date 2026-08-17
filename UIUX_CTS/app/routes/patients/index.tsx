import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Download, Search, ChevronRight } from "lucide-react";
import { AppShell, PageHeader, SafetyNote } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "../__root";

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
  const { session } = useAuth();
  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const { data: searchResults, isLoading, isError, error } = useQuery({
    queryKey: ["patientsSearch", query],
    queryFn: async () => {
      if (!session?.access_token) return [];
      const response = await fetch(`/api/patients/search?query=${query}`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      if (!response.ok) {
        throw new Error("Failed to search patients");
      }
      return response.json();
    },
    enabled: !!session?.access_token,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(searchInput);
  };

  return (
    <AppShell>
      <PageHeader
        title="All Patients & Encounters"
        subtitle="Search patient history to run the clinical orchestration workflow."
      />

      <div className="mb-6 bg-card p-6 rounded-lg shadow-sm border border-border">
        <h2 className="text-lg font-medium text-foreground mb-4 flex items-center gap-2">
          <Search className="w-5 h-5" /> Search Patient History
        </h2>
        <form onSubmit={handleSearch} className="flex flex-col gap-3 sm:flex-row mb-2">
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Enter Patient ID or Name"
            className="flex-1"
          />
          <Button type="submit" variant="default" className="sm:w-32">
            Search
          </Button>
        </form>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground bg-muted/20">
              <th className="px-6 py-4 font-medium">Patient ID</th>
              <th className="px-6 py-4 font-medium">Patient Name</th>
              <th className="px-6 py-4 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {isLoading && (
              <tr>
                <td colSpan={3} className="px-6 py-12 text-center text-sm text-muted-foreground">
                  Searching...
                </td>
              </tr>
            )}
            {isError && (
              <tr>
                <td colSpan={3} className="px-6 py-12 text-center text-sm text-destructive">
                  Error: {(error as Error).message}
                </td>
              </tr>
            )}
            {!isLoading && !isError && searchResults?.map((r: any, i: number) => (
              <tr key={i} className="hover:bg-muted/40 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap font-medium text-foreground">
                  {r.PATIENT_ID}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-muted-foreground">
                  Patient {r.PATIENT_ID.substring(0, 8)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap font-medium text-right">
                  <Button
                    variant="default"
                    size="sm"
                    className="gap-1"
                    onClick={() => {
                      navigate({
                        to: `/patients/${r.PATIENT_ID}`,
                        search: { encounterId: r.ENCOUNTER_ID },
                      });
                    }}
                  >
                    View <ChevronRight className="w-4 h-4" />
                  </Button>
                </td>
              </tr>
            ))}
            {!isLoading && !isError && searchResults?.length === 0 && query !== "" && (
              <tr>
                <td colSpan={3} className="px-6 py-12 text-center text-sm text-muted-foreground">
                  No patients match this search.
                </td>
              </tr>
            )}
            {!isLoading && !isError && searchResults?.length === 0 && query === "" && (
              <tr>
                <td colSpan={3} className="px-6 py-12 text-center text-sm text-muted-foreground">
                  Enter a query to search patients.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-8">
        <SafetyNote text="This list relies on the actual Synthea/EHR patient source used by the Care Manager flow." />
      </div>
    </AppShell>
  );
}
