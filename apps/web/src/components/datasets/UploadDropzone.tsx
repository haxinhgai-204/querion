"use client";

import { useCallback, useRef, useState } from "react";
import { useI18n } from "@/components/providers/I18nProvider";

interface Props {
  datasetId: string;
  onUploadComplete: () => void;
}

export default function UploadDropzone({ datasetId, onUploadComplete }: Props) {
  const { t } = useI18n();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);

  const uploadFiles = useCallback(async (files: FileList | File[]) => {
    const { api } = await import("@/lib/api");
    const fileArr = Array.from(files);
    if (fileArr.length === 0) return;

    setUploading(true);
    setProgress([]);

    for (const file of fileArr) {
      try {
        setProgress((prev) => [...prev, `Uploading ${file.name}...`]);
        const formData = new FormData();
        formData.append("file", file);
        await api.upload(`/v1/datasets/${datasetId}/documents/upload`, formData);
        setProgress((prev) => [...prev.slice(0, -1), `✓ ${file.name}`]);
      } catch (err: any) {
        setProgress((prev) => [...prev.slice(0, -1), `✗ ${file.name}: ${err.message}`]);
      }
    }

    setUploading(false);
    onUploadComplete();
    setTimeout(() => setProgress([]), 3000);
  }, [datasetId, onUploadComplete]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
  }, [uploadFiles]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      // Capture files into array BEFORE resetting input
      // (FileList is a live reference that gets cleared when input value is reset)
      const fileArray = Array.from(files);
      e.target.value = "";
      uploadFiles(fileArray);
    }
  }, [uploadFiles]);

  const openFilePicker = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  return (
    <div
      className="rounded-xl p-6 text-center transition-all duration-200 cursor-pointer"
      style={{
        border: `2px dashed ${dragging ? "var(--accent)" : "var(--border)"}`,
        background: dragging ? "var(--accent-glow)" : "var(--card)",
      }}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={openFilePicker}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        multiple
        style={{ display: "none" }}
        onChange={handleFileSelect}
        onClick={(e) => e.stopPropagation()}
      />

      <svg width="40" height="40" viewBox="0 0 40 40" fill="none" className="mx-auto mb-3">
        <path d="M20 8V24M14 14L20 8L26 14" stroke={dragging ? "var(--accent)" : "var(--muted)"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M8 28V30C8 31.1046 8.89543 32 10 32H30C31.1046 32 32 31.1046 32 30V28" stroke={dragging ? "var(--accent)" : "var(--muted)"} strokeWidth="2" strokeLinecap="round" />
      </svg>

      {uploading ? (
        <p className="text-sm font-medium" style={{ color: "var(--accent)" }}>
          {t("upload.uploading", "datasets")}
        </p>
      ) : (
        <>
          <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
            {t("upload.title", "datasets")}
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
            {t("upload.subtitle", "datasets")}
          </p>
        </>
      )}

      {progress.length > 0 && (
        <div className="mt-3 text-left text-xs space-y-1">
          {progress.map((msg, i) => (
            <p key={i} style={{ color: msg.startsWith("✗") ? "#ef4444" : msg.startsWith("✓") ? "#22c55e" : "var(--muted)" }}>
              {msg}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

