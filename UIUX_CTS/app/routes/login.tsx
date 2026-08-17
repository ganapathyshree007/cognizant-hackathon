import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AlertCircle, Stethoscope, HeartPulse } from "lucide-react";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isSignUp, setIsSignUp] = useState(false);
  const [fullName, setFullName] = useState("");

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (isSignUp) {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: {
            data: {
              full_name: fullName,
              role: "CARE_MANAGER", // Strictly Care Manager
            },
          },
        });
        if (error) throw error;
        
        if (data.session) {
          localStorage.removeItem("patient_token");
          navigate({ to: "/" });
        } else {
          alert("Sign up successful! Please check your email to verify your account or sign in if auto-confirm is on.");
          setIsSignUp(false);
        }
      } else {
        const { data, error } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (error) throw error;
        localStorage.removeItem("patient_token");
        navigate({ to: "/" });
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans selection:bg-teal-100 selection:text-teal-900">
      
      {/* Left Side - Visual / Branding */}
      <div className="hidden lg:flex w-1/2 bg-teal-900 relative overflow-hidden flex-col justify-between p-12">
        <div className="absolute inset-0 bg-gradient-to-br from-teal-800 to-teal-950 z-0 opacity-90" />
        {/* Abstract medical shapes background */}
        <div className="absolute -top-24 -left-24 w-96 h-96 bg-teal-700/20 rounded-full blur-3xl z-0" />
        <div className="absolute top-1/2 right-0 w-80 h-80 bg-cyan-700/20 rounded-full blur-3xl z-0" />

        <div className="relative z-10 flex items-center gap-3 text-white">
          <HeartPulse className="w-8 h-8" />
          <span className="text-2xl font-bold tracking-tight">CarePath</span>
        </div>

        <div className="relative z-10 max-w-lg">
          <h1 className="text-4xl lg:text-5xl font-semibold text-white leading-tight mb-6 tracking-tight">
            Advanced Care Orchestration
          </h1>
          <p className="text-teal-100/80 text-lg leading-relaxed">
            Empowering Care Managers with data-driven insights, streamlined workflows, and intelligent patient tracking to deliver exceptional care.
          </p>
        </div>

        <div className="relative z-10 text-teal-200/60 text-sm">
          &copy; {new Date().getFullYear()} CarePath Health Systems. All rights reserved.
        </div>
      </div>

      {/* Right Side - Form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-12">
        <div className="w-full max-w-md bg-white p-8 sm:p-12 rounded-2xl shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100 relative">
          
          <div className="lg:hidden flex items-center gap-2 text-teal-900 mb-8 justify-center">
            <HeartPulse className="w-6 h-6" />
            <span className="text-xl font-bold tracking-tight">CarePath</span>
          </div>

          <div className="text-center mb-10">
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900 mb-2">
              {isSignUp ? "Care Manager Signup" : "Welcome back"}
            </h2>
            <p className="text-slate-500">
              {isSignUp ? "Create an account to access the platform." : "Please sign in to your Care Manager account."}
            </p>
          </div>

          <form className="space-y-5" onSubmit={handleAuth}>
            {error && (
              <div className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 shadow-sm">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5 text-red-500" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}

            {isSignUp && (
              <div className="space-y-1.5">
                <Label htmlFor="fullName" className="text-slate-700 font-medium">Full Name</Label>
                <Input
                  id="fullName"
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="h-12 bg-slate-50 border-slate-200 focus:border-teal-500 focus:ring-teal-500 rounded-xl"
                  placeholder="Dr. Jane Doe"
                />
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-slate-700 font-medium">Email Address</Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 bg-slate-50 border-slate-200 focus:border-teal-500 focus:ring-teal-500 rounded-xl"
                placeholder="jane.doe@carepath.com"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-slate-700 font-medium">Password</Label>
              <Input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-12 bg-slate-50 border-slate-200 focus:border-teal-500 focus:ring-teal-500 rounded-xl"
                placeholder="••••••••"
              />
            </div>

            <Button 
              type="submit" 
              disabled={loading} 
              className="w-full h-12 bg-teal-800 hover:bg-teal-900 text-white rounded-xl font-medium text-base shadow-lg shadow-teal-900/20 transition-all mt-4"
            >
              {loading ? "Processing..." : isSignUp ? "Create Account" : "Sign In"}
            </Button>
          </form>

          <div className="mt-8 pt-8 border-t border-slate-100 text-center space-y-4">
            <p className="text-sm text-slate-500">
              {isSignUp ? "Already have an account?" : "Need a Care Manager account?"}{" "}
              <button
                onClick={() => setIsSignUp(!isSignUp)}
                className="font-semibold text-teal-700 hover:text-teal-800 transition-colors"
              >
                {isSignUp ? "Sign In instead" : "Sign Up"}
              </button>
            </p>
            <div className="text-sm text-slate-500">
              Are you a patient?{" "}
              <a href="/patient-login" className="font-semibold text-indigo-600 hover:text-indigo-700 transition-colors">
                Go to Patient Portal
              </a>
            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
