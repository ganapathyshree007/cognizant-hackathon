import { Link, useRouterState } from "@tanstack/react-router";
import { LayoutGrid, Users, Building2, PhoneCall, ClipboardList, Menu, ShieldCheck } from "lucide-react";
import { useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import { useAuth } from "../routes/__root";

const nav = [
  { title: "Overview", to: "/", icon: LayoutGrid, exact: true },
  { title: "Patients", to: "/patients", icon: Users, exact: false },
  { title: "Care Assessment", to: "/care-assessment", icon: ClipboardList, exact: false },
  { title: "Appointments", to: "/follow-ups", icon: PhoneCall, exact: false },
  { title: "Providers", to: "/providers", icon: Building2, exact: false },
] as const;

const patientNav = [
  { title: "My Care (Patient View)", to: "/my-care", icon: ShieldCheck, exact: false },
] as const;

function NavList({ onNavigate }: { onNavigate?: (() => void) | undefined }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { role } = useAuth();

  return (
    <nav className="flex flex-col gap-0.5">
      {role === "CARE_MANAGER" && nav.map((item) => {
        const active = item.exact ? pathname === item.to : pathname.startsWith(item.to);
        return (
          <Link
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
              active
                ? "bg-accent font-medium text-accent-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <item.icon className="size-4" strokeWidth={1.75} />
            {item.title}
          </Link>
        );
      })}

      {role === "PATIENT" && (
        <>
          <div className="mt-4 mb-2 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Patient Portal
          </div>
          {patientNav.map((item) => {
            const active = item.exact ? pathname === item.to : pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                onClick={onNavigate}
                className={cn(
                  "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm transition-colors",
                  active
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                <item.icon className="size-4" strokeWidth={1.75} />
                {item.title}
              </Link>
            );
          })}
        </>
      )}
    </nav>
  );
}

function SidebarInner({ onNavigate }: { onNavigate?: (() => void) | undefined }) {
  const { role } = useAuth();
  
  const handleLogout = async () => {
    try {
      await supabase.auth.signOut();
      sessionStorage.clear();
      localStorage.clear();
      window.location.href = role === "PATIENT" ? "/patient-login" : "/login";
    } catch (e) {
      console.error("Logout failed", e);
      window.location.href = role === "PATIENT" ? "/patient-login" : "/login";
    }
  };

  return (
    <div className="flex h-full flex-col justify-between px-4 py-6">
      <div className="space-y-8">
        <Link to="/" onClick={onNavigate} className="flex items-center gap-2 px-3">
          <span className="size-2.5 rounded-full bg-primary" />
          <span className="text-sm font-semibold tracking-tight">CarePath</span>
        </Link>
        <NavList onNavigate={onNavigate} />
      </div>

      <div className="flex flex-col gap-3 border-t border-border px-3 pt-4">
        {role === "CARE_MANAGER" ? (
          <div className="flex items-center gap-3">
            <span className="flex size-8 items-center justify-center rounded-full bg-muted text-xs font-medium text-muted-foreground">
              JM
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">Jordan Mills</p>
              <p className="truncate text-xs text-muted-foreground">Care manager</p>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <span className="flex size-8 items-center justify-center rounded-full bg-primary/20 text-primary text-xs font-medium">
              PT
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">Verified Patient</p>
              <p className="truncate text-xs text-muted-foreground">Patient Portal</p>
            </div>
          </div>
        )}
        <button 
          onClick={handleLogout}
          className="text-xs font-medium text-muted-foreground hover:text-foreground text-left py-1"
        >
          Log out
        </button>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <aside className="fixed inset-y-0 left-0 hidden w-60 border-r border-border bg-card md:block">
        <SidebarInner />
      </aside>

      <div className="md:pl-60">
        <header className="flex items-center gap-3 border-b border-border bg-card px-4 py-3 md:hidden">
          <button
            aria-label="Toggle navigation"
            onClick={() => setOpen((v) => !v)}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted"
          >
            <Menu className="size-5" strokeWidth={1.75} />
          </button>
          <span className="text-sm font-semibold">CarePath</span>
        </header>
        {open ? (
          <div className="border-b border-border bg-card md:hidden">
            <SidebarInner onNavigate={() => setOpen(false)} />
          </div>
        ) : null}

        <main className="mx-auto w-full max-w-5xl px-6 py-10 md:px-10 md:py-14">{children}</main>
      </div>
    </div>
  );
}

export function PageHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="mb-10">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-1.5 text-sm text-muted-foreground">{subtitle}</p>
    </div>
  );
}

export function SafetyNote({ text }: { text: string }) {
  return (
    <p className="rounded-lg border border-border bg-muted/50 px-4 py-3 text-xs leading-relaxed text-muted-foreground">
      {text}
    </p>
  );
}
