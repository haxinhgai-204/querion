"use client";

import { useI18n } from "@/components/providers/I18nProvider";

export default function ChatPage() {
  const { t } = useI18n();

  return (
    <div className="flex flex-col h-full">
      <div className="mb-6">
        <h2 className="text-xl font-semibold" style={{ color: "var(--foreground)" }}>
          {t("title", "chat")}
        </h2>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          {t("description", "chat")}
        </p>
      </div>

      <div
        className="flex-1 flex flex-col items-center justify-center rounded-xl"
        style={{ border: "1px dashed var(--border)", background: "var(--card)" }}
      >
        <div
          className="flex items-center justify-center rounded-full mb-4"
          style={{
            width: 64,
            height: 64,
            background: "var(--accent-glow)",
          }}
        >
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M5 5H23C23.5523 5 24 5.44772 24 6V20C24 20.5523 23.5523 21 23 21H10L5 26V6C5 5.44772 5.44772 5 6 5H5Z" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M10 11H18" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round"/>
            <path d="M10 15H14" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round"/>
          </svg>
        </div>
        <p className="text-sm font-medium" style={{ color: "var(--muted)" }}>
          {t("startConversation", "chat")}
        </p>
        <p className="text-xs mt-1" style={{ color: "var(--muted)", opacity: 0.7 }}>
          {t("selectApp", "chat")}
        </p>
      </div>

      <div className="mt-4">
        <div
          className="flex items-center gap-3 rounded-xl px-4 py-3"
          style={{ background: "var(--card)", border: "1px solid var(--border)" }}
        >
          <input
            id="chat-input"
            type="text"
            placeholder={t("inputPlaceholder", "chat")}
            disabled
            className="flex-1 bg-transparent text-sm outline-none"
            style={{ color: "var(--foreground)" }}
          />
          <button
            id="btn-send-message"
            disabled
            className="rounded-lg px-4 py-1.5 text-sm font-medium text-white opacity-50"
            style={{ background: "var(--accent)" }}
          >
            {t("buttons.send")}
          </button>
        </div>
      </div>
    </div>
  );
}
