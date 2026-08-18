import { createFileRoute } from "@tanstack/react-router";
import { AppShell, PageHeader } from "@/components/app-shell";
import { Users, ActivitySquare, CalendarDays, PhoneCall, TrendingDown, ArrowRight, Play, AlertTriangle } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";
import { Button } from "@/components/ui/button";
import { useState, useEffect } from "react";
import { getPatientName } from "@/lib/utils";

export const Route = createFileRoute("/")(
  {
    component: DashboardOverview,
  }
);

const DEFAULT_STATS = {
  total_patients: 803,
  needing_assessment: 12,
  upcoming_appointments: 0,
  follow_ups_due: 0,
};

const NYU_CATEGORIES = [
  { name: "Non-Emergent", value: 31, color: "#0d9488" },
  { name: "Emergent, PC Treatable", value: 24, color: "#6366f1" },
  { name: "Emergent, Avoidable", value: 18, color: "#f59e0b" },
  { name: "Emergent, Not Avoidable", value: 27, color: "#94a3b8" },
];

const MONTHLY_TREND = [
  { month: "Mar", avoidable: 42, nonAvoidable: 31 },
  { month: "Apr", avoidable: 38, nonAvoidable: 28 },
  { month: "May", avoidable: 45, nonAvoidable: 33 },
  { month: "Jun", avoidable: 35, nonAvoidable: 30 },
  { month: "Jul", avoidable: 32, nonAvoidable: 29 },
  { month: "Aug", avoidable: 28, nonAvoidable: 27 },
];

const RECENT_ACTIVITY = [
  { action: "Assessment completed", patient: "James Smith", time: "12 min ago", type: "assessment" },
  { action: "Appointment scheduled", patient: "Mary Johnson", time: "1 hr ago", type: "appointment" },
  { action: "Outreach call recorded", patient: "Robert Williams", time: "2 hrs ago", type: "outreach" },
  { action: "Care pathway approved", patient: "Linda Brown", time: "3 hrs ago", type: "approval" },
  { action: "Follow-up marked complete", patient: "Patricia Jones", time: "5 hrs ago", type: "followup" },
];

function DashboardOverview() {
  const [stats, setStats] = useState(DEFAULT_STATS);
  const [flaggedMembers, setFlaggedMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      setLoading(true);
      try {
        // 1. Fetch statistics from backend API
        const statsRes = await fetch("/api/dashboard/stats");
        if (statsRes.ok) {
          setStats(await statsRes.json());
        }

        // 2. Fetch top 3 high-risk patients via backend (uses service key, bypasses RLS)
        const flaggedRes = await fetch("/api/patients/flagged");
        if (flaggedRes.ok) {
          const bData = await flaggedRes.json();
          const mapped = bData.map((p: any) => ({
            name: getPatientName(p.PATIENT_ID, p.gender),
            id: p.PATIENT_ID,
            visits: p.target_repeat_ed_90d || 0,
            pattern: p.target_repeat_ed_90d > 1 ? "Repeat ED visits" : "Potential Care Gap",
            risk: p.target_repeat_ed_90d > 0 ? "HIGH" : "MEDIUM",
            encounterId: p.ENCOUNTER_ID
          }));
          setFlaggedMembers(mapped);
        }
      } catch (e) {
        console.error("Error loading dashboard data:", e);
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  return (
    <AppShell>
      <PageHeader
        title="Dashboard"
        subtitle="Care Manager Overview — Avoidable ED Utilization Navigator."
        actions={
          <Link to="/care-assessment">
            <Button className="gap-2">
              <Play className="w-3.5 h-3.5" /> New Assessment
            </Button>
          </Link>
        }
      />
      
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-card border border-border p-5 rounded-xl shadow-sm flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Users className="w-4 h-4" />
            <span className="text-xs font-medium">Total Active Members</span>
          </div>
          <div className="text-2xl font-bold text-foreground">{stats.total_patients}</div>
          <span className="text-xs text-muted-foreground">Across all care programs</span>
        </div>

        <div className="bg-card border border-border p-5 rounded-xl shadow-sm flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-destructive">
            <ActivitySquare className="w-4 h-4" />
            <span className="text-xs font-medium">Needing Assessment</span>
          </div>
          <div className="text-2xl font-bold text-foreground">{stats.needing_assessment}</div>
          <span className="text-xs text-muted-foreground">Flagged for care navigation review</span>
        </div>

        <div className="bg-card border border-border p-5 rounded-xl shadow-sm flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-blue-500">
            <CalendarDays className="w-4 h-4" />
            <span className="text-xs font-medium">Upcoming Appointments</span>
          </div>
          <div className="text-2xl font-bold text-foreground">{stats.upcoming_appointments}</div>
          <span className="text-xs text-muted-foreground">Scheduled in system</span>
        </div>

        <div className="bg-card border border-border p-5 rounded-xl shadow-sm flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-amber-500">
            <PhoneCall className="w-4 h-4" />
            <span className="text-xs font-medium">Follow-ups Due</span>
          </div>
          <div className="text-2xl font-bold text-foreground">{stats.follow_ups_due}</div>
          <span className="text-xs text-muted-foreground">Outreach calls pending</span>
        </div>
      </div>

      {/* ED Utilization Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
        
        {/* NYU Classification Breakdown */}
        <div className="bg-card border border-border rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-foreground">ED Visit Classification</h2>
              <p className="text-xs text-muted-foreground mt-0.5">NYU Algorithm — Last 6 Months</p>
            </div>
            <Link to="/analytics" className="text-xs text-primary hover:underline">
              View Details →
            </Link>
          </div>
          <div className="flex items-center gap-6">
            <div className="w-40 h-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={NYU_CATEGORIES}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={70}
                    dataKey="value"
                    stroke="none"
                  >
                    {NYU_CATEGORIES.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
                    formatter={(value: number) => [`${value}%`, '']}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex-1 space-y-2.5">
              {NYU_CATEGORIES.map((cat) => (
                <div key={cat.name} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: cat.color }} />
                    <span className="text-muted-foreground text-xs">{cat.name}</span>
                  </div>
                  <span className="font-medium text-xs">{cat.value}%</span>
                </div>
              ))}
            </div>
          </div>
          <p className="text-[11px] text-muted-foreground mt-4 border-t border-border pt-3">
            Classification uses the NYU ED Algorithm at the population level — not a judgment of any individual visit.
          </p>
        </div>

        {/* Monthly Trend */}
        <div className="bg-card border border-border rounded-xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Monthly ED Trend</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Potentially Avoidable vs. Non-Avoidable</p>
            </div>
            <div className="flex items-center gap-1 text-green-600 text-xs font-medium">
              <TrendingDown className="w-3.5 h-3.5" />
              <span>↓ 33% avoidable</span>
            </div>
          </div>
          <div className="h-44">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={MONTHLY_TREND} barGap={2}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} width={30} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }} />
                <Bar dataKey="avoidable" name="Potentially Avoidable" fill="#f59e0b" radius={[3, 3, 0, 0]} maxBarSize={24} />
                <Bar dataKey="nonAvoidable" name="Non-Avoidable" fill="#94a3b8" radius={[3, 3, 0, 0]} maxBarSize={24} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Flagged Members + Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-8">
        
        {/* Flagged Members */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-foreground">Flagged Members — Priority Queue</h2>
            <Link to="/patients" className="text-xs text-primary hover:underline">View All</Link>
          </div>
          <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/20">
                <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
                  <th className="px-5 py-3">Member</th>
                  <th className="px-5 py-3">ED Visits (6mo)</th>
                  <th className="px-5 py-3">Pattern</th>
                  <th className="px-5 py-3">Risk</th>
                  <th className="px-5 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {flaggedMembers.map((m) => (
                  <tr key={m.id} className="hover:bg-muted/40 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="font-medium text-foreground">{m.name}</div>
                      <div className="text-xs text-muted-foreground font-mono">{m.id}</div>
                    </td>
                    <td className="px-5 py-3.5 font-medium">{m.visits}</td>
                    <td className="px-5 py-3.5 text-muted-foreground text-xs">{m.pattern}</td>
                    <td className="px-5 py-3.5">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        m.risk === "HIGH" ? "bg-destructive/10 text-destructive" : "bg-amber-100 text-amber-700"
                      }`}>
                        {m.risk}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <Link to="/care-assessment" search={{ patientId: m.id, encounterId: m.encounterId }}>
                        <Button variant="outline" size="sm" className="gap-1 text-xs">
                          Assess <ArrowRight className="w-3 h-3" />
                        </Button>
                      </Link>
                    </td>
                  </tr>
                ))}
                {flaggedMembers.length === 0 && !loading && (
                  <tr>
                    <td colSpan={5} className="px-5 py-8 text-center text-muted-foreground">No flagged members found.</td>
                  </tr>
                )}
                {loading && (
                  <tr>
                    <td colSpan={5} className="px-5 py-8 text-center text-muted-foreground animate-pulse">Loading priority queue...</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Activity */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-foreground">Recent Activity</h2>
          </div>
          <div className="bg-card border border-border rounded-xl shadow-sm p-4 space-y-0">
            {RECENT_ACTIVITY.map((item, idx) => (
              <div key={idx} className={`flex items-start gap-3 py-3 ${idx < RECENT_ACTIVITY.length - 1 ? 'border-b border-border' : ''}`}>
                <div className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${
                  item.type === 'assessment' ? 'bg-primary' :
                  item.type === 'appointment' ? 'bg-blue-500' :
                  item.type === 'outreach' ? 'bg-amber-500' :
                  item.type === 'approval' ? 'bg-green-500' :
                  'bg-muted-foreground'
                }`} />
                <div className="min-w-0">
                  <p className="text-xs font-medium text-foreground">{item.action}</p>
                  <p className="text-xs text-muted-foreground">{item.patient} · {item.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Safety Disclaimer */}
      <div className="mt-8">
        <p className="rounded-lg border border-border bg-muted/50 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
          All classifications use the NYU ED Algorithm at the population level. This dashboard identifies care navigation opportunities — it does not judge whether any individual ED visit was appropriate. If a member is experiencing a medical emergency, emergency care should never be discouraged.
        </p>
      </div>
    </AppShell>
  );
}
