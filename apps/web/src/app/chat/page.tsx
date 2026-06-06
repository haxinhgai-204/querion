"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, getAccessToken, getActiveWorkspaceId } from "@/lib/api";
import { listApps, AppResponse } from "@/lib/api/apps";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Array<{ filename: string; content: string; score?: number }> | null;
}

interface Conversation {
  id: string;
  title: string;
  message_count: number;
  updated_at: string;
}

export default function ChatPage() {
  const [apps, setApps] = useState<AppResponse[]>([]);
  const [selectedApp, setSelectedApp] = useState<AppResponse | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConv, setSelectedConv] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [loadingMsgs, setLoadingMsgs] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load apps
  useEffect(() => {
    listApps().then(setApps).catch(() => { });
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load conversations when app selected
  const loadConversations = useCallback(async (appId: string) => {
    try {
      const convs = await api.get<Conversation[]>(`/v1/apps/${appId}/conversations`);
      setConversations(convs);
    } catch { setConversations([]); }
  }, []);

  const selectApp = useCallback((app: AppResponse) => {
    setSelectedApp(app);
    setSelectedConv(null);
    setMessages([]);
    loadConversations(app.id);
  }, [loadConversations]);

  const selectConversation = useCallback(async (convId: string) => {
    setSelectedConv(convId);
    setLoadingMsgs(true);
    try {
      const msgs = await api.get<Message[]>(`/v1/conversations/${convId}/messages`);
      setMessages(msgs);
    } catch { setMessages([]); }
    finally { setLoadingMsgs(false); }
  }, []);

  const startNewConversation = useCallback(() => {
    setSelectedConv(null);
    setMessages([]);
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || streaming || !selectedApp) return;
    const userText = input.trim();
    setInput("");
    setStreaming(true);

    // Optimistic user message
    const tempUserMsg: Message = { id: `tmp-${Date.now()}`, role: "user", content: userText };
    setMessages(prev => [...prev, tempUserMsg]);

    // Streaming assistant placeholder
    const tempAssistantId = `stream-${Date.now()}`;
    setMessages(prev => [...prev, { id: tempAssistantId, role: "assistant", content: "" }]);

    try {
      const body: any = { message: userText };
      if (selectedConv) body.conversation_id = selectedConv;

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/v1/apps/${selectedApp.id}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${getAccessToken()}`,
          "X-Workspace-Id": getActiveWorkspaceId() || "",
        },
        body: JSON.stringify(body),
      });

      if (!response.ok || !response.body) {
        throw new Error("Stream failed");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullContent = "";
      let sources: any[] = [];
      let newConvId: string | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        const lines = text.split("\n");

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6).trim();
          if (data === "[DONE]") continue;
          try {
            const parsed = JSON.parse(data);
            if (parsed.type === "conversation_id") {
              newConvId = parsed.conversation_id;
              if (!selectedConv) setSelectedConv(parsed.conversation_id);
            } else if (parsed.type === "token") {
              fullContent += parsed.content;
              setMessages(prev => prev.map(m => m.id === tempAssistantId ? { ...m, content: fullContent } : m));
            } else if (parsed.type === "sources") {
              sources = parsed.sources || [];
              setMessages(prev => prev.map(m => m.id === tempAssistantId ? { ...m, sources } : m));
            } else if (parsed.type === "title") {
              if (newConvId) {
                setConversations(prev => prev.map(c => c.id === newConvId ? { ...c, title: parsed.title } : c));
              }
            }
          } catch { /* ignore */ }
        }
      }

      // Refresh conversations after message
      if (selectedApp) {
        loadConversations(selectedApp.id);
      }
    } catch (err) {
      setMessages(prev => prev.map(m => m.id === tempAssistantId ? { ...m, content: "⚠️ Failed to get response. Please try again." } : m));
    } finally {
      setStreaming(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex h-full gap-0" style={{ height: "calc(100vh - 80px)" }}>
      {/* Left sidebar: App picker + Conversations */}
      <div className="flex flex-col w-64 flex-shrink-0 rounded-xl overflow-hidden mr-3" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        {/* Apps */}
        <div className="p-3 border-b" style={{ borderColor: "var(--border)" }}>
          <p className="text-[10px] font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--muted)" }}>Select App</p>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {apps.length === 0 && <p className="text-xs" style={{ color: "var(--muted)" }}>No apps available</p>}
            {apps.map(app => (
              <button key={app.id} onClick={() => selectApp(app)}
                className="w-full text-left rounded-lg px-2.5 py-1.5 text-xs transition-all"
                style={{
                  background: selectedApp?.id === app.id ? "var(--accent)" : "transparent",
                  color: selectedApp?.id === app.id ? "#fff" : "var(--foreground)",
                }}>
                <div className="flex items-center gap-1.5">
                  <span>{app.name}</span>
                  {app.is_published && <span className="text-[9px] px-1 rounded-full" style={{ background: "rgba(34,197,94,0.2)", color: "#22c55e" }}>live</span>}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Conversations */}
        {selectedApp && (
          <div className="flex-1 flex flex-col overflow-hidden p-3">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: "var(--muted)" }}>Conversations</p>
              <button onClick={startNewConversation}
                className="text-[10px] px-2 py-0.5 rounded-md font-medium"
                style={{ background: "var(--accent-glow)", color: "var(--accent)" }}>
                + New
              </button>
            </div>
            <div className="flex-1 overflow-y-auto space-y-1">
              {conversations.length === 0 && <p className="text-[11px]" style={{ color: "var(--muted)" }}>No conversations yet</p>}
              {conversations.map(conv => (
                <button key={conv.id} onClick={() => selectConversation(conv.id)}
                  className="w-full text-left rounded-lg px-2.5 py-2 text-xs transition-all"
                  style={{
                    background: selectedConv === conv.id ? "rgba(99,102,241,0.1)" : "transparent",
                    border: selectedConv === conv.id ? "1px solid rgba(99,102,241,0.3)" : "1px solid transparent",
                    color: "var(--foreground)",
                  }}>
                  <div className="truncate font-medium">{conv.title || "New Chat"}</div>
                  <div className="text-[10px] mt-0.5" style={{ color: "var(--muted)" }}>{conv.message_count} messages</div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col rounded-xl overflow-hidden" style={{ background: "var(--card)", border: "1px solid var(--border)" }}>
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b flex-shrink-0" style={{ borderColor: "var(--border)" }}>
          <div>
            <h2 className="text-sm font-semibold" style={{ color: "var(--foreground)" }}>
              {selectedApp ? selectedApp.name : "Chat"}
            </h2>
            <p className="text-[11px]" style={{ color: "var(--muted)" }}>
              {selectedApp ? (selectedConv ? "Conversation" : "New conversation") : "Select an app to start chatting"}
            </p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {!selectedApp ? (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="rounded-full p-4 mb-4" style={{ background: "var(--accent-glow)" }}>
                <svg width="32" height="32" viewBox="0 0 28 28" fill="none"><path d="M5 5H23C23.5523 5 24 5.44772 24 6V20C24 20.5523 23.5523 21 23 21H10L5 26V6C5 5.44772 5.44772 5 6 5H5Z" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /><path d="M10 11H18" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" /><path d="M10 15H14" stroke="var(--accent)" strokeWidth="1.5" strokeLinecap="round" /></svg>
              </div>
              <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>Start a conversation</p>
              <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>Select an app from the sidebar to begin</p>
            </div>
          ) : loadingMsgs ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-current" style={{ borderTopColor: "transparent", color: "var(--accent)" }} />
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full">
              <p className="text-sm" style={{ color: "var(--muted)" }}>Type a message below to start chatting with <strong>{selectedApp.name}</strong></p>
            </div>
          ) : (
            messages.map(msg => (
              <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className="max-w-[75%]">
                  <div className="rounded-2xl px-4 py-2.5 text-sm"
                    style={{
                      background: msg.role === "user" ? "var(--accent)" : "var(--background)",
                      color: msg.role === "user" ? "#fff" : "var(--foreground)",
                      border: msg.role === "assistant" ? "1px solid var(--border)" : "none",
                      whiteSpace: "pre-wrap",
                    }}>
                    {msg.content || <span className="animate-pulse">●●●</span>}
                  </div>
                  {/* Sources */}
                  {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {msg.sources.slice(0, 3).map((src, i) => (
                        <div key={i} className="rounded-lg px-3 py-1.5 text-[11px]"
                          style={{ background: "rgba(99,102,241,0.06)", border: "1px solid rgba(99,102,241,0.15)", color: "var(--muted)" }}>
                          <span className="font-semibold" style={{ color: "var(--accent)" }}>#{i + 1}</span> {src.filename} — {src.content?.slice(0, 80)}...
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t flex-shrink-0" style={{ borderColor: "var(--border)" }}>
          <div className="flex items-end gap-3 rounded-xl px-4 py-3" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
            <textarea
              ref={inputRef}
              id="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={selectedApp ? `Message ${selectedApp.name}... (Enter to send)` : "Select an app first"}
              disabled={!selectedApp || streaming}
              rows={1}
              className="flex-1 bg-transparent text-sm outline-none resize-none"
              style={{ color: "var(--foreground)", maxHeight: 120 }}
            />
            <button
              id="btn-send-message"
              onClick={sendMessage}
              disabled={!selectedApp || !input.trim() || streaming}
              className="rounded-lg px-4 py-1.5 text-sm font-medium flex-shrink-0 transition-opacity"
              style={{ background: "var(--accent)", color: "#fff", opacity: (!selectedApp || !input.trim() || streaming) ? 0.5 : 1 }}>
              {streaming ? (
                <span className="flex items-center gap-1.5">
                  <span className="animate-spin rounded-full h-3 w-3 border border-white" style={{ borderTopColor: "transparent" }} />
                  Thinking
                </span>
              ) : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
