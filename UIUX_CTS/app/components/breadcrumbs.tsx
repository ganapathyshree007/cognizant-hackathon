import { Link } from "@tanstack/react-router";
import { ChevronRight, ArrowLeft } from "lucide-react";

type BreadcrumbItem = {
  label: string;
  to?: string;
};

export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  const backTo = items.length >= 2 ? items[items.length - 2].to : undefined;

  return (
    <div className="mb-6 flex items-center gap-2">
      {backTo && (
        <Link
          to={backTo}
          className="mr-1 inline-flex items-center justify-center rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          aria-label="Go back"
        >
          <ArrowLeft className="size-4" strokeWidth={1.75} />
        </Link>
      )}
      <nav className="flex items-center gap-1 text-sm" aria-label="Breadcrumb">
        {items.map((item, idx) => {
          const isLast = idx === items.length - 1;
          return (
            <span key={idx} className="flex items-center gap-1">
              {idx > 0 && (
                <ChevronRight className="size-3.5 text-muted-foreground/50 shrink-0" />
              )}
              {isLast || !item.to ? (
                <span className={isLast ? "font-medium text-foreground" : "text-muted-foreground"}>
                  {item.label}
                </span>
              ) : (
                <Link
                  to={item.to}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  {item.label}
                </Link>
              )}
            </span>
          );
        })}
      </nav>
    </div>
  );
}
