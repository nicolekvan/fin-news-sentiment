"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/news/", label: "AI News Feed" },
  { href: "/screener/", label: "Screener" },
  { href: "/performance/", label: "Model Performance" },
];

export function SiteNav() {
  const path = usePathname();
  return (
    <nav aria-label="Main" className="flex flex-wrap gap-1">
      {LINKS.map((l) => {
        const active = l.href === "/" ? path === "/" : path.startsWith(l.href.replace(/\/$/, ""));
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "whitespace-nowrap rounded-md px-2.5 py-1.5 text-xs font-medium text-muted hover:text-text",
              active && "bg-panel-2 text-text",
            )}
          >
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
