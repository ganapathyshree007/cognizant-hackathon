import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { ShieldCheck, ArrowRight, ActivitySquare, HeartPulse } from "lucide-react";
import { useAuth } from "./__root";
import { supabase } from "@/lib/supabase";

export const Route = createFileRoute("/patient-login")({
  component: PatientLogin,
});

function PatientLogin() {
  const [patientId, setPatientId] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { patientToken } = useAuth();

  if (patientToken) {
    navigate({ to: "/my-care" });
    return null;
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId.trim()) {
      setError("Please enter your Patient ID.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const res = await fetch("/api/patient/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ patient_id: patientId.trim() })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Patient ID not found. Please check your ID and try again.");
      }

      const data = await res.json();
      await supabase.auth.signOut(); // Clear any stale Care Manager session
      localStorage.setItem("patient_token", data.token);
      window.location.href = "/my-care";
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans selection:bg-indigo-100 selection:text-indigo-900">
      
      {/* Left Side - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12 order-2 lg:order-1">
        <div className="w-full max-w-md bg-white p-8 sm:p-12 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 relative">
          
          <div className="lg:hidden flex items-center gap-2 text-indigo-900 mb-8 justify-center">
            <HeartPulse className="w-6 h-6" />
            <span className="text-xl font-bold tracking-tight">CarePath</span>
          </div>

          <div className="text-center mb-10">
            <div className="inline-flex items-center justify-center p-3 bg-indigo-50 text-indigo-600 rounded-2xl mb-6">
              <ShieldCheck className="w-8 h-8" />
            </div>
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-2">
              Patient Portal
            </h2>
            <p className="text-slate-500">
              Enter your secure Patient ID to access your care dashboard.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-5">
            {error && (
              <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 shadow-sm">
                <ActivitySquare className="w-5 h-5 shrink-0 mt-0.5 text-red-500" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}
            
            <div className="space-y-1.5">
              <label htmlFor="patientId" className="text-slate-700 font-medium text-sm">
                Patient ID
              </label>
              <input
                id="patientId"
                type="text"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                placeholder="e.g. 00126cb9-..."
                className="w-full h-12 px-4 rounded-xl border border-slate-200 bg-slate-50 focus:border-indigo-500 focus:ring-indigo-500 transition-colors"
                required
              />
            </div>
            
            <button
              type="submit"
              disabled={loading}
              className="w-full h-12 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium text-base shadow-lg shadow-indigo-600/20 transition-all mt-4 flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {loading ? "Verifying..." : "Access My Care"}
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>
          
          <div className="mt-8 pt-8 border-t border-slate-100 text-center">
            <p className="text-sm text-slate-500">
              Are you a Care Manager?{" "}
              <a href="/login" className="font-semibold text-indigo-600 hover:text-indigo-700 transition-colors">
                Sign in here
              </a>
            </p>
          </div>
        </div>
      </div>

      {/* Right Side - Visual / Branding */}
      <div className="hidden lg:flex w-1/2 bg-indigo-900 relative overflow-hidden flex-col justify-between p-12 order-1 lg:order-2">
        <div className="absolute inset-0 bg-gradient-to-bl from-indigo-800 to-indigo-950 z-0 opacity-90" />
        
        {/* Abstract medical shapes background */}
        <div className="absolute -bottom-24 -right-24 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl z-0" />
        <div className="absolute top-1/3 left-0 w-80 h-80 bg-blue-500/20 rounded-full blur-3xl z-0" />

        <div className="relative z-10 flex items-center gap-3 text-white justify-end">
          <span className="text-2xl font-bold tracking-tight">CarePath</span>
          <HeartPulse className="w-8 h-8" />
        </div>

        <div className="relative z-10 max-w-lg self-end text-right">
          <h1 className="text-4xl lg:text-5xl font-semibold text-white leading-tight mb-6 tracking-tight">
            Your Health,<br/>In Your Hands
          </h1>
          <p className="text-indigo-100/80 text-lg leading-relaxed ml-auto max-w-md">
            Securely access your medical records, upcoming appointments, and personal care pathways directly from our trusted patient portal.
          </p>
        </div>

        <div className="relative z-10 text-indigo-200/60 text-sm text-right">
          &copy; {new Date().getFullYear()} CarePath Health Systems.
        </div>
      </div>

    </div>
  );
}
