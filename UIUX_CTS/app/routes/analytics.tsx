import { createFileRoute } from "@tanstack/react-router";
import { AppShell, PageHeader, SafetyNote } from "@/components/app-shell";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { DollarSign, Users, TrendingDown, Target } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend,
} from "recharts";

export const Route = createFileRoute("/analytics")({
  head: () => ({ meta: [{ title: "Management Analytics — CarePath" }] }),
  component: AnalyticsPage,
});

// ── Mock Analytics Data ──
const COST_METRICS = {
  totalEdVisits: 1243,
  potentiallyAvoidable: 456,
  avgEdCost: 2032,
  avgAltCost: 287,
  estimatedSavings: 796_020,
  avoidableRate: 36.7,
};

const MONTHLY_TREND = [
  { month: "Jan", avoidable: 78, total: 210 },
  { month: "Feb", avoidable: 82, total: 205 },
  { month: "Mar", avoidable: 75, total: 198 },
  { month: "Apr", avoidable: 68, total: 202 },
  { month: "May", avoidable: 62, total: 195 },
  { month: "Jun", avoidable: 55, total: 190 },
  { month: "Jul", avoidable: 48, total: 185 },
  { month: "Aug", avoidable: 42, total: 178 },
];

const NYU_BREAKDOWN = [
  { name: "Non-Emergent", value: 187, pct: 15.0, color: "#0d9488" },
  { name: "Emergent, PC Treatable", value: 269, pct: 21.6, color: "#6366f1" },
  { name: "Emergent, Avoidable", value: 143, pct: 11.5, color: "#f59e0b" },
  { name: "Emergent, Not Avoidable", value: 412, pct: 33.1, color: "#94a3b8" },
  { name: "Injury", value: 98, pct: 7.9, color: "#ef4444" },
  { name: "Behavioral Health", value: 78, pct: 6.3, color: "#8b5cf6" },
  { name: "Substance Use", value: 56, pct: 4.5, color: "#ec4899" },
];

const PATHWAY_DISTRIBUTION = [
  { pathway: "Primary Care", members: 156, pct: 34.2, color: "#0d9488" },
  { pathway: "Urgent Care", members: 112, pct: 24.6, color: "#6366f1" },
  { pathway: "Telehealth", members: 98, pct: 21.5, color: "#f59e0b" },
  { pathway: "Care Management", members: 90, pct: 19.7, color: "#94a3b8" },
];

const TOP_PATTERNS = [
  { pattern: "Repeat evening/weekend visits, low-acuity discharge", count: 89, trend: "↓ 12%" },
  { pattern: "Chronic condition flare-ups between appointments", count: 76, trend: "↓ 8%" },
  { pattern: "No established primary care relationship", count: 64, trend: "→ 0%" },
  { pattern: "Transportation or access barriers documented", count: 52, trend: "↓ 15%" },
  { pattern: "Post-discharge follow-up gaps", count: 41, trend: "↓ 6%" },
  { pattern: "Medication management / refill visits", count: 34, trend: "↓ 22%" },
];

const OUTREACH_OUTCOMES = [
  { month: "Mar", contacted: 45, navigated: 28, noResponse: 12, declined: 5 },
  { month: "Apr", contacted: 52, navigated: 34, noResponse: 13, declined: 5 },
  { month: "May", contacted: 48, navigated: 31, noResponse: 10, declined: 7 },
  { month: "Jun", contacted: 55, navigated: 38, noResponse: 11, declined: 6 },
  { month: "Jul", contacted: 60, navigated: 42, noResponse: 12, declined: 6 },
  { month: "Aug", contacted: 58, navigated: 45, noResponse: 9, declined: 4 },
];

function AnalyticsPage() {
  return (
    <AppShell>
      <Breadcrumbs items={[
        { label: "Dashboard", to: "/" },
        { label: "Management Analytics" },
      ]} />
      <PageHeader
        title="Management Analytics"
        subtitle="Aggregate trends and cost-avoidance opportunity for leadership review."
      />

      {/* Cost-Avoidance Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-card border border-border p-5 rounded-xl shadow-sm">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Users className="w-4 h-4" />
            <span className="text-xs font-medium">ED Visits (12mo)</span>
          </div>
          <div className="text-2xl font-bold">{COST_METRICS.totalEdVisits.toLocaleString()}</div>
          <span className="text-xs text-muted-foreground">{COST_METRICS.potentiallyAvoidable} potentially avoidable</span>
        </div>

        <div className="bg-card border border-border p-5 rounded-xl shadow-sm">
          <div className="flex items-center gap-2 text-muted-foreground mb-1">
            <Target className="w-4 h-4" />
            <span className="text-xs font-medium">Avoidable Rate</span>
          </div>
          <div className="text-2xl font-bold">{COST_METRICS.avoidableRate}%</div>
          <span className="text-xs text-muted-foreground">Population-level classification</span>
        </div>

        <div className="bg-card border border-border p-5 rounded-xl shadow-sm">
          <div className="flex items-center gap-2 text-green-600 mb-1">
            <DollarSign className="w-4 h-4" />
            <span className="text-xs font-medium">Est. Cost-Avoidance Opportunity</span>
          </div>
          <div className="text-2xl font-bold">${(COST_METRICS.estimatedSavings / 1000).toFixed(0)}K</div>
          <span className="text-xs text-muted-foreground">Based on avg ED vs. alternative cost</span>
        </div>

        <div className="bg-card border border-border p-5 rounded-xl shadow-sm">
          <div className="flex items-center gap-2 text-primary mb-1">
            <TrendingDown className="w-4 h-4" />
            <span className="text-xs font-medium">Trend (MoM)</span>
          </div>
          <div className="text-2xl font-bold text-green-600">↓ 46%</div>
          <span className="text-xs text-muted-foreground">Avoidable visits Jan → Aug</span>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
        
        {/* Monthly Trend Line */}
        <div className="bg-card border border-border rounded-xl shadow-sm p-6">
          <h2 className="text-sm font-semibold text-foreground mb-1">Monthly ED Visit Trend</h2>
          <p className="text-xs text-muted-foreground mb-4">Total vs. Potentially Avoidable</p>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={MONTHLY_TREND}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} width={35} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }} />
                <Line type="monotone" dataKey="total" name="Total Visits" stroke="#94a3b8" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="avoidable" name="Potentially Avoidable" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* NYU Category Breakdown */}
        <div className="bg-card border border-border rounded-xl shadow-sm p-6">
          <h2 className="text-sm font-semibold text-foreground mb-1">NYU ED Algorithm Breakdown</h2>
          <p className="text-xs text-muted-foreground mb-4">Visit classification distribution (12mo)</p>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={NYU_BREAKDOWN} layout="vertical" barSize={16}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
                <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: '#64748b' }} width={130} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }} />
                <Bar dataKey="value" name="Visits" radius={[0, 4, 4, 0]}>
                  {NYU_BREAKDOWN.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Pathway + Outreach */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8">
        
        {/* Pathway Distribution */}
        <div className="bg-card border border-border rounded-xl shadow-sm p-6">
          <h2 className="text-sm font-semibold text-foreground mb-1">Recommended Pathway Distribution</h2>
          <p className="text-xs text-muted-foreground mb-4">Members by recommended care alternative</p>
          <div className="flex items-center gap-8">
            <div className="w-40 h-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={PATHWAY_DISTRIBUTION} cx="50%" cy="50%" innerRadius={40} outerRadius={70} dataKey="members" stroke="none">
                    {PATHWAY_DISTRIBUTION.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex-1 space-y-3">
              {PATHWAY_DISTRIBUTION.map((p) => (
                <div key={p.pathway} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: p.color }} />
                    <span className="text-xs text-muted-foreground">{p.pathway}</span>
                  </div>
                  <div className="text-right">
                    <span className="text-xs font-medium">{p.members}</span>
                    <span className="text-xs text-muted-foreground ml-1">({p.pct}%)</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Outreach Outcomes */}
        <div className="bg-card border border-border rounded-xl shadow-sm p-6">
          <h2 className="text-sm font-semibold text-foreground mb-1">Outreach Outcomes</h2>
          <p className="text-xs text-muted-foreground mb-4">Member navigation results by month</p>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={OUTREACH_OUTCOMES} barGap={1}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#94a3b8' }} width={30} />
                <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }} />
                <Bar dataKey="navigated" name="Successfully Navigated" fill="#0d9488" radius={[3, 3, 0, 0]} maxBarSize={18} />
                <Bar dataKey="noResponse" name="No Response" fill="#94a3b8" radius={[3, 3, 0, 0]} maxBarSize={18} />
                <Bar dataKey="declined" name="Declined" fill="#f59e0b" radius={[3, 3, 0, 0]} maxBarSize={18} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Top Patterns Table */}
      <div className="mt-8">
        <h2 className="text-sm font-semibold text-foreground mb-3">Top Utilization Patterns</h2>
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/20">
              <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
                <th className="px-5 py-3">#</th>
                <th className="px-5 py-3">Pattern Description</th>
                <th className="px-5 py-3">Members</th>
                <th className="px-5 py-3">Trend (MoM)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {TOP_PATTERNS.map((p, i) => (
                <tr key={i} className="hover:bg-muted/40 transition-colors">
                  <td className="px-5 py-3.5 font-medium text-muted-foreground">{i + 1}</td>
                  <td className="px-5 py-3.5 text-foreground">{p.pattern}</td>
                  <td className="px-5 py-3.5 font-medium">{p.count}</td>
                  <td className="px-5 py-3.5">
                    <span className={`text-xs font-medium ${p.trend.includes('↓') ? 'text-green-600' : 'text-muted-foreground'}`}>
                      {p.trend}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cost Methodology */}
      <div className="mt-8 bg-card border border-border rounded-xl shadow-sm p-6">
        <h3 className="text-sm font-semibold text-foreground mb-2">Cost-Avoidance Methodology</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-xs text-muted-foreground block mb-0.5">Avg. ED Visit Cost</span>
            <span className="font-medium">${COST_METRICS.avgEdCost.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block mb-0.5">Avg. Alternative Visit Cost</span>
            <span className="font-medium">${COST_METRICS.avgAltCost.toLocaleString()}</span>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block mb-0.5">Savings per Redirected Visit</span>
            <span className="font-medium">${(COST_METRICS.avgEdCost - COST_METRICS.avgAltCost).toLocaleString()}</span>
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground mt-4 border-t border-border pt-3">
          Estimates are illustrative using synthetic data. Actual cost-avoidance requires validated claims-based cost data and does not account for clinical complexity or member preferences.
        </p>
      </div>

      <div className="mt-6">
        <SafetyNote text="All analytics are population-level summaries based on the NYU ED Algorithm classification. They identify care navigation opportunities, not judgments about individual visits." />
      </div>
    </AppShell>
  );
}
