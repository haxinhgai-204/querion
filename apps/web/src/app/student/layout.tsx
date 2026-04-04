"use client";

import { StudentSettingsProvider } from "@/components/providers/StudentSettingsProvider";

export default function StudentLayout({ children }: { children: React.ReactNode }) {
  return <StudentSettingsProvider>{children}</StudentSettingsProvider>;
}
