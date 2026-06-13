"use client";

import { usePathname } from "next/navigation";
import ThemeToggle from "@/components/ui/ThemeToggle";
import LanguageSwitcher from "@/components/ui/LanguageSwitcher";
import WorkspaceSwitcher from "@/components/ui/WorkspaceSwitcher";
import { useI18n } from "@/components/providers/I18nProvider";

function getPageTitleKey(pathname: string): string {
  if (pathname.startsWith("/admin/users")) return "Users";
  if (pathname.startsWith("/admin/workspaces")) return "Workspaces";
  if (pathname.startsWith("/admin/settings")) return "Settings";
  if (pathname.startsWith("/admin/students")) return "Students";
  const segments = pathname.split("/").filter(Boolean);
  if (segments.length === 0) return "nav.datasets";
  return `nav.${segments[0]}`;
}

export default function Topbar() {
  const pathname = usePathname();
  const { t } = useI18n();
  const titleKey = getPageTitleKey(pathname);

  // For admin pages, use title directly; for feature pages, use i18n
  const title = titleKey.startsWith("nav.") ? t(titleKey) : titleKey;

  return (
    <header
      id="topbar"
      className="flex items-center justify-between px-6"
      style={{
        height: "var(--topbar-height)",
        borderBottom: "1px solid var(--border)",
        background: "var(--background)",
      }}
    >
      <div className="flex items-center gap-3">
        {/* Mobile hamburger */}
        <button
          id="mobile-menu-btn"
          style={{ display: "none", color: "var(--foreground)" }}
          className="items-center justify-center rounded-lg p-1.5"
          onClick={() => {
            document.getElementById("sidebar")?.classList.toggle("open");
            document.getElementById("sidebar-overlay")?.classList.toggle("open");
          }}
        >
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <path d="M3 6H19M3 11H19M3 16H19" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
        <h1 className="text-base font-semibold" style={{ color: "var(--foreground)" }}>
          {title}
        </h1>
      </div>

      <div className="flex items-center gap-3">
        <LanguageSwitcher />
        <ThemeToggle />
        <WorkspaceSwitcher />
      </div>
    </header>
  );
}
