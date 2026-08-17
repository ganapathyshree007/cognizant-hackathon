import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  useNavigate,
} from "@tanstack/react-router";
import { useEffect, useState, createContext, useContext } from "react";
import { supabase } from "../lib/supabase";
import { Session } from "@supabase/supabase-js";
import { reportLovableError } from "../lib/lovable-error-reporting";

type AuthContextType = {
  session: Session | null;
  patientToken: string | null;
  role: "CARE_MANAGER" | "PATIENT" | null;
  loading: boolean;
};

const AuthContext = createContext<AuthContextType>({ session: null, patientToken: null, role: null, loading: true });

export const useAuth = () => useContext(AuthContext);

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6">
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();
  useEffect(() => {
    reportLovableError(error, { boundary: "tanstack_root_error_component" });
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <div className="max-w-md text-center">
        <h1 className="text-xl font-semibold tracking-tight text-foreground">
          This page didn't load
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Something went wrong on our end. You can try refreshing or head back home.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Try again
          </button>
          <a
            href="/"
            className="inline-flex items-center justify-center rounded-md border border-input bg-background px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
          >
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootComponent() {
  const { queryClient } = Route.useRouteContext();
  const [session, setSession] = useState<Session | null>(null);
  const [patientToken, setPatientToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    // Check patient token first
    const pt = localStorage.getItem("patient_token");
    if (pt) {
      setPatientToken(pt);
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (loading) return;
    const path = window.location.pathname;
    
    const hasCmSession = !!session;
    const hasPtSession = !!patientToken;

    // Determine the active role
    let activeRole: "CARE_MANAGER" | "PATIENT" | null = null;
    if (hasCmSession && hasPtSession) {
      // If both somehow exist (stale session), resolve based on route to force the correct auth flow
      activeRole = path.startsWith("/my-care") ? "PATIENT" : "CARE_MANAGER";
    } else if (hasCmSession) {
      activeRole = "CARE_MANAGER";
    } else if (hasPtSession) {
      activeRole = "PATIENT";
    }

    if (path === "/login") {
      if (activeRole === "CARE_MANAGER") navigate({ to: "/" });
      else if (activeRole === "PATIENT") navigate({ to: "/my-care" });
      return;
    }
    
    if (path === "/patient-login") {
      if (activeRole === "PATIENT") navigate({ to: "/my-care" });
      else if (activeRole === "CARE_MANAGER") navigate({ to: "/" });
      return;
    }

    const isPatientRoute = path.startsWith("/my-care");
    
    if (isPatientRoute) {
      if (activeRole !== "PATIENT") {
        navigate({ to: "/patient-login" });
      }
    } else {
      if (activeRole !== "CARE_MANAGER") {
        navigate({ to: "/login" });
      }
    }
  }, [session, patientToken, loading, navigate, window.location.pathname]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  let activeRole: "CARE_MANAGER" | "PATIENT" | null = null;
  if (session && patientToken) {
    activeRole = window.location.pathname.startsWith("/my-care") ? "PATIENT" : "CARE_MANAGER";
  } else if (session) {
    activeRole = "CARE_MANAGER";
  } else if (patientToken) {
    activeRole = "PATIENT";
  }

  return (
    <AuthContext.Provider value={{ session, patientToken, role: activeRole, loading }}>
      <QueryClientProvider client={queryClient}>
        <Outlet />
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}
