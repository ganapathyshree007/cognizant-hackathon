import { createFileRoute, Link, notFound, useNavigate } from "@tanstack/react-router";
import { ArrowLeft, CheckCircle2, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";
import { AppShell, SafetyNote } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { usePatient, setPatientStatus } from "@/lib/care-store";
import { SAFETY_NOTE } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/call-review/$patientId")({
  head: () => ({
    meta: [
      { title: "Call review — CarePath Care Navigation" },
      {
        name: "description",
        content:
          "Guided call review combining reported current symptoms with historical utilization context.",
      },
      { property: "og:title", content: "Call review — CarePath" },
      {
        property: "og:description",
        content: "Guided call review for care managers speaking with a patient.",
      },
    ],
  }),
  component: CallReview,
  notFoundComponent: Missing,
});

function Missing() {
  return (
    <AppShell>
      <h1 className="text-2xl font-semibold tracking-tight">Patient not found</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        <Link to="/patients" className="underline">
          Back to patients
        </Link>
      </p>
    </AppShell>
  );
}

const SEVERE = [
  "Severe or rapidly worsening symptoms",
  "Chest pain or severe breathing difficulty",
  "Fainting or new severe confusion",
  "Significant bleeding",
  "Other concerning/high-risk symptom",
];
const OTHER = ["Symptoms are mild or stable", "Needs same-day assessment", "Routine or follow-up concern"];

type Decision = "emergency" | "same-day" | "routine" | "unsure";

const decisions: { value: Decision; label: string }[] = [
  { value: "emergency", label: "Emergency evaluation" },
  { value: "same-day", label: "Same-day care" },
  { value: "routine", label: "Routine primary care / follow-up" },
  { value: "unsure", label: "Unsure / clinician review" },
];

function CallReview() {
  const { patientId } = Route.useParams();
  const patient = usePatient(patientId);
  const navigate = useNavigate();
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [recorded, setRecorded] = useState(false);

  if (!patient) throw notFound();

  const hasSevere = symptoms.some((s) => SEVERE.includes(s));
  const effective: Decision | null = useMemo(() => {
    if (hasSevere) return "emergency";
    return decision;
  }, [hasSevere, decision]);

  const toggle = (s: string) =>
    setSymptoms((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));

  const lowerAcuity = effective === "same-day" || effective === "routine";

  return (
    <AppShell>
      <Link
        to="/patients/$patientId"
        params={{ patientId: patient.id }}
        className="mb-8 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4" strokeWidth={1.75} />
        Patient detail
      </Link>

      <header>
        <h1 className="text-2xl font-semibold tracking-tight">Call review</h1>
        <p className="mt-1.5 text-sm">
          {patient.name} · <span className="text-muted-foreground">{patient.mrn}</span>
        </p>
        <p className="mt-3 max-w-2xl text-sm text-muted-foreground">
          Review the patient’s current symptoms together with their historical record. This supports
          the care workflow and does not replace clinical judgment.
        </p>
      </header>

      <section className="mt-12">
        <h2 className="text-sm font-medium">Step 1 — Current symptoms reported</h2>
        <div className="mt-4 space-y-1 rounded-xl border border-border bg-card p-3">
          {[...SEVERE, ...OTHER].map((s) => (
            <label
              key={s}
              className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-3.5 text-sm hover:bg-muted/50"
            >
              <Checkbox checked={symptoms.includes(s)} onCheckedChange={() => toggle(s)} />
              <span>{s}</span>
            </label>
          ))}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="text-sm font-medium">Step 2 — Care decision</h2>
        <RadioGroup
          value={effective ?? ""}
          onValueChange={(v) => setDecision(v as Decision)}
          className="mt-4 grid gap-3 sm:grid-cols-2"
        >
          {decisions.map((d) => (
            <label
              key={d.value}
              className={cn(
                "flex cursor-pointer items-center gap-3 rounded-xl border bg-card px-5 py-4 text-sm transition-colors",
                effective === d.value ? "border-primary/40 bg-primary/5" : "border-border hover:bg-muted/40",
              )}
            >
              <RadioGroupItem value={d.value} id={d.value} />
              <Label htmlFor={d.value} className="cursor-pointer font-normal">
                {d.label}
              </Label>
            </label>
          ))}
        </RadioGroup>
        {hasSevere ? (
          <p className="mt-3 text-xs text-muted-foreground">
            A concerning current symptom is selected, so the pathway stays at emergency evaluation.
            Current symptoms always take priority over historical utilization.
          </p>
        ) : null}
      </section>

      <section className="mt-12">
        <h2 className="text-sm font-medium">Step 3 — Historical context</h2>
        <p className="mt-1.5 text-xs text-muted-foreground">
          Supporting information only. It does not describe the patient’s current condition.
        </p>
        <dl className="mt-4 divide-y divide-border rounded-xl border border-border bg-muted/30 px-6 text-sm">
          {[
            ["ED visits in last 6 months", String(patient.edVisits6mo)],
            ["Recent similar ED visits", patient.pattern],
            ["Previous disposition pattern", "Most encounters discharged same day"],
            [
              "Existing primary-care relationship",
              patient.suggested === "Primary Care" ? "None on file" : "Established",
            ],
            ["Previous suggested care pathway", patient.suggested],
          ].map(([k, v]) => (
            <div key={k} className="flex flex-col gap-1 py-4 sm:flex-row sm:justify-between sm:gap-8">
              <dt className="text-muted-foreground">{k}</dt>
              <dd className="sm:text-right">{v}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-12">
        <h2 className="text-sm font-medium">Step 4 — Recommendation / next action</h2>
        <div
          className={cn(
            "mt-4 rounded-xl border p-6 text-sm",
            effective === "emergency"
              ? "border-amber-300 bg-amber-50 text-amber-900"
              : "border-border bg-card",
          )}
        >
          {effective === "emergency" ? (
            <div className="flex gap-3">
              <ShieldAlert className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} />
              <p>
                Based on the information entered, emergency evaluation may be appropriate. Follow
                clinical protocols and local escalation procedures.
              </p>
            </div>
          ) : effective === "same-day" ? (
            <p>
              Same-day care may be appropriate. Care options to discuss: Urgent Care, Telehealth, or
              a same-day clinic appointment.
            </p>
          ) : effective === "routine" ? (
            <p>
              A routine pathway may be appropriate. Care options to discuss: Primary Care or Care
              Management enrollment.
            </p>
          ) : effective === "unsure" ? (
            <p>
              The information is not sufficient for a clear pathway. Escalate for clinician review.
            </p>
          ) : (
            <p className="text-muted-foreground">
              Select the reported symptoms and a care decision to see a suggested next action.
            </p>
          )}
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          The care manager and clinical team make the final decision. Historical utilization is
          context only.
        </p>
      </section>

      <div className="mt-10 flex flex-wrap items-center gap-3">
        <Button
          onClick={() => {
            setRecorded(true);
            setPatientStatus(
              patient.id,
              effective === "routine" || effective === "same-day" ? "Outreach sent" : "Needs review",
              effective === "emergency"
                ? "Emergency evaluation discussed"
                : effective === "unsure"
                  ? "Escalated for clinician review"
                  : "Await patient response",
            );
          }}
          disabled={!effective}
        >
          Record review
        </Button>
        {lowerAcuity ? (
          <Button
            variant="outline"
            onClick={() => navigate({ to: "/providers", search: { care: patient.suggested } })}
          >
            Send care options
          </Button>
        ) : null}
        {effective === "unsure" ? (
          <Button
            variant="outline"
            onClick={() => {
              setRecorded(true);
              setPatientStatus(patient.id, "Needs review", "Escalated for clinician review");
            }}
          >
            Escalate for clinician review
          </Button>
        ) : null}
        {recorded ? (
          <span className="inline-flex items-center gap-1.5 text-sm text-primary">
            <CheckCircle2 className="size-4" strokeWidth={1.75} />
            Review recorded
          </span>
        ) : null}
      </div>

      <div className="mt-10">
        <SafetyNote text={SAFETY_NOTE} />
      </div>
    </AppShell>
  );
}
