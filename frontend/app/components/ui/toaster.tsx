import { Toaster as SonnerToaster } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      position="top-right"
      toastOptions={{
        style: {
          background: "white",
          border: "1px solid hsl(0 0% 90%)",
          color: "hsl(0 0% 15%)",
          fontSize: "13px",
          boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
        },
      }}
      closeButton
      richColors
    />
  );
}
