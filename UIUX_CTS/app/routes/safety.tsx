import { createFileRoute } from "@tanstack/react-router";
import { AppShell, PageHeader } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { ShieldCheck, ShieldAlert, AlertTriangle, CheckCircle2, XCircle, ArrowRight, Info } from "lucide-react";

export const Route = createFileRoute("/safety")({
  head: () => ({ meta: [{ title: "Safety Framework — CarePath" }] }),
  component: SafetyFrameworkPage,
});

function SafetyFrameworkPage() {
  return (
    <AppShell>
      <Breadcrumbs items={[
        { label: "Dashboard", to: "/" },
        { label: "Safety Framework" },
      ]} />
      <PageHeader
        title="Safety Framework"
        subtitle="How this system ensures legitimate emergency care is never discouraged or restricted."
      />

      {/* Core Principle */}
      <div className="bg-card border border-border rounded-xl shadow-sm p-6 mb-8">
        <div className="flex items-start gap-4">
          <div className="p-2.5 rounded-lg bg-primary/10 text-primary shrink-0">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-foreground mb-2">Core Safety Principle</h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              This system is designed as a <strong className="text-foreground">care navigation support tool</strong>, not a triage or gatekeeping system. 
              It identifies <em>patterns</em> of ED utilization at the member level to help care managers connect members with 
              appropriate alternatives — <strong className="text-foreground">it never evaluates whether any individual ED visit was appropriate</strong>, 
              and it never discourages a member from seeking emergency care when they believe they need it.
            </p>
          </div>
        </div>
      </div>

      {/* What the System Does / Does NOT */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        
        {/* Does */}
        <div className="bg-card border border-border rounded-xl shadow-sm p-6">
          <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-green-600" /> What This System Does
          </h3>
          <ul className="space-y-3">
            {[
              "Identifies members with recurring patterns of potentially avoidable ED use based on claims data",
              "Classifies patterns using the published NYU ED Algorithm at the population level",
              "Provides plain-language explanations of utilization patterns to care managers",
              "Recommends a specific lower-acuity care option (PCP, Urgent Care, Telehealth, Care Mgmt)",
              "Routes recommendations to care managers who make the final outreach decision",
              "Maintains a complete audit trail of every recommendation and decision",
              "Frames every output as a future care navigation option, never a correction",
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-600 mt-0.5 shrink-0" />
                <span className="text-muted-foreground">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Does NOT */}
        <div className="bg-card border border-border rounded-xl shadow-sm p-6">
          <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <XCircle className="w-4 h-4 text-destructive" /> What This System Does NOT Do
          </h3>
          <ul className="space-y-3">
            {[
              "Judge whether any individual ED visit was appropriate or inappropriate",
              "Determine real-time clinical severity or triage urgency",
              "Block, discourage, or delay any member from accessing emergency care",
              "Contact members directly — all outreach goes through the care manager",
              "Surface evaluative language about past visits to the member",
              "Override clinical judgment of the care team or treating physicians",
              "Use the classification as a prior-authorization or claims-denial tool",
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm">
                <XCircle className="w-3.5 h-3.5 text-destructive mt-0.5 shrink-0" />
                <span className="text-muted-foreground">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Safety Gate Flow */}
      <div className="bg-card border border-border rounded-xl shadow-sm p-6 mb-8">
        <h3 className="text-sm font-semibold text-foreground mb-4">Safety Gate — Current Condition Assessment</h3>
        <p className="text-xs text-muted-foreground mb-6">
          When a care manager enters current symptoms and measurements, the deterministic Safety Gate assigns a status:
        </p>
        
        <div className="flex flex-col md:flex-row items-stretch gap-4">
          {/* RED */}
          <div className="flex-1 rounded-xl border-2 border-red-200 bg-red-50/50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-4 h-4 rounded-full bg-red-500" />
              <span className="font-semibold text-red-800 text-sm">RED — Emergency</span>
            </div>
            <p className="text-xs text-red-700 leading-relaxed mb-3">
              Current symptoms indicate a potentially life-threatening condition. The system halts all routine recommendations.
            </p>
            <div className="bg-red-100 rounded-lg px-3 py-2 text-xs text-red-800 font-medium">
              Action: "Seek immediate emergency care. Do not delay."
            </div>
          </div>

          <div className="hidden md:flex items-center">
            <ArrowRight className="w-5 h-5 text-muted-foreground/30" />
          </div>

          {/* YELLOW */}
          <div className="flex-1 rounded-xl border-2 border-amber-200 bg-amber-50/50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-4 h-4 rounded-full bg-amber-500" />
              <span className="font-semibold text-amber-800 text-sm">YELLOW — Urgent Review</span>
            </div>
            <p className="text-xs text-amber-700 leading-relaxed mb-3">
              Symptoms require timely clinical evaluation but may not be immediately life-threatening.
            </p>
            <div className="bg-amber-100 rounded-lg px-3 py-2 text-xs text-amber-800 font-medium">
              Action: "Urgent clinical review recommended within hours."
            </div>
          </div>

          <div className="hidden md:flex items-center">
            <ArrowRight className="w-5 h-5 text-muted-foreground/30" />
          </div>

          {/* GREEN */}
          <div className="flex-1 rounded-xl border-2 border-green-200 bg-green-50/50 p-5">
            <div className="flex items-center gap-2 mb-3">
              <span className="w-4 h-4 rounded-full bg-green-500" />
              <span className="font-semibold text-green-800 text-sm">GREEN — Routine Navigation</span>
            </div>
            <p className="text-xs text-green-700 leading-relaxed mb-3">
              No acute safety signals detected. The system may suggest alternative care options for the care manager to review.
            </p>
            <div className="bg-green-100 rounded-lg px-3 py-2 text-xs text-green-800 font-medium">
              Action: "Review provider options and discuss with member."
            </div>
          </div>
        </div>

        <p className="text-[11px] text-muted-foreground mt-5 border-t border-border pt-3">
          The Safety Gate is deterministic (rule-based), not AI-driven. It applies hard-coded clinical thresholds and cannot be overridden by the AI explanation layer.
        </p>
      </div>

      {/* AI Layer Guardrails */}
      <div className="bg-card border border-border rounded-xl shadow-sm p-6 mb-8">
        <h3 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-500" /> AI Explanation Layer — Safety Guardrails
        </h3>
        <p className="text-xs text-muted-foreground mb-5">
          The LLM explanation layer operates under an explicit safety instruction set. The following constraints are enforced:
        </p>
        <div className="space-y-3">
          {[
            {
              rule: "No retrospective judgment",
              desc: "The AI layer must never state or imply that a past ED visit was 'unnecessary', 'inappropriate', or 'avoidable'."
            },
            {
              rule: "Forward-looking framing only",
              desc: "Every recommendation must be phrased as a future option: 'For similar concerns in the future, consider...' — never 'You should not have gone to the ED.'"
            },
            {
              rule: "Pattern-level language",
              desc: "Explanations describe member-level utilization patterns, never single-visit determinations."
            },
            {
              rule: "Safety Gate supremacy",
              desc: "If the Safety Gate is RED or YELLOW, the AI layer cannot override it or recommend a lower-acuity option."
            },
            {
              rule: "Human-in-the-loop",
              desc: "All AI outputs are presented to the care manager for review. The care manager — not the model — decides whether and how to act."
            },
            {
              rule: "No direct member contact",
              desc: "AI-generated text is never delivered directly to a member. It is a tool for the care manager's internal use."
            },
          ].map((g, i) => (
            <div key={i} className="flex items-start gap-3 p-3 bg-muted/30 rounded-lg border border-border">
              <div className="mt-0.5 w-5 h-5 rounded-full bg-amber-100 text-amber-600 flex items-center justify-center text-[10px] font-bold shrink-0">
                {i + 1}
              </div>
              <div>
                <span className="text-sm font-medium text-foreground">{g.rule}</span>
                <p className="text-xs text-muted-foreground mt-0.5">{g.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* NYU Algorithm Disclaimer */}
      <div className="bg-card border border-border rounded-xl shadow-sm p-6 mb-8">
        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
          <Info className="w-4 h-4 text-blue-500" /> NYU ED Algorithm — Limitations
        </h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-start gap-2">
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-muted-foreground/50 shrink-0" />
            The NYU ED Algorithm is a claims-based, retrospective classification method. It was not designed as a triage tool.
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-muted-foreground/50 shrink-0" />
            It assigns <em>probabilities</em> across categories — no visit is labeled with certainty as "avoidable."
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-muted-foreground/50 shrink-0" />
            Recent literature (JAMA Network Open, 2024) cautions against using discharge-diagnosis-based classification to judge single-visit appropriateness.
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-muted-foreground/50 shrink-0" />
            This project uses the algorithm strictly as intended: a population-level signal feeding member-pattern detection, never a determination about any one visit.
          </li>
        </ul>
      </div>

      {/* Audit Trail Summary */}
      <div className="bg-card border border-border rounded-xl shadow-sm p-6">
        <h3 className="text-sm font-semibold text-foreground mb-4">Audit Trail Summary</h3>
        <p className="text-xs text-muted-foreground mb-4">
          Every system recommendation and care manager decision is logged with a timestamp, decision rationale, and outcome.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/20">
              <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
                <th className="px-4 py-2.5">Timestamp</th>
                <th className="px-4 py-2.5">Member</th>
                <th className="px-4 py-2.5">System Recommendation</th>
                <th className="px-4 py-2.5">CM Decision</th>
                <th className="px-4 py-2.5">Rationale</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border text-xs">
              {[
                { ts: "Aug 18, 10:32 AM", member: "Marcus Bell", rec: "Primary Care Follow-up", decision: "Approved", reason: "Member confirmed interest in PCP establishment" },
                { ts: "Aug 17, 3:15 PM", member: "Alina Okafor", rec: "Urgent Care Referral", decision: "Approved", reason: "Weekend pattern matches UC availability" },
                { ts: "Aug 17, 11:00 AM", member: "Robert Chen", rec: "Care Management Enrollment", decision: "Escalated", reason: "Chronic condition complexity — clinical review needed" },
                { ts: "Aug 16, 2:45 PM", member: "Denise Hartley", rec: "Telehealth Intake", decision: "Approved", reason: "Transportation barrier confirmed — telehealth preferred" },
                { ts: "Aug 16, 9:20 AM", member: "Javier Ruiz", rec: "Primary Care Establishment", decision: "Approved", reason: "New to service area — no PCP on file" },
              ].map((row, i) => (
                <tr key={i} className="hover:bg-muted/40 transition-colors">
                  <td className="px-4 py-3 text-muted-foreground whitespace-nowrap">{row.ts}</td>
                  <td className="px-4 py-3 font-medium text-foreground">{row.member}</td>
                  <td className="px-4 py-3 text-muted-foreground">{row.rec}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      row.decision === 'Approved' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-700'
                    }`}>
                      {row.decision}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground max-w-[200px] truncate">{row.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}
