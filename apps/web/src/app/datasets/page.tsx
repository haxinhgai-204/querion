"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useI18n } from "@/components/providers/I18nProvider";
import {
  listDatasets,
  createDataset,
  deleteDataset,
  getDatasetUsage,
  DatasetResponse,
  DatasetUsageResponse,
} from "@/lib/api/datasets";
import CreateDatasetModal from "@/components/datasets/CreateDatasetModal";
import ConfirmDialog from "@/components/ui/ConfirmDialog";

export default function DatasetsPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [datasets, setDatasets] = useState<DatasetResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [deleteUsage, setDeleteUsage] = useState<DatasetUsageResponse | null>(null);
  const [checkingUsage, setCheckingUsage] = useState(false);

  const fetchDatasets = useCallback(async () => {//lấy danh sách dts
    try {
      const data = await listDatasets();
      setDatasets(data);
    } catch {
      // silent — may not have workspace selected
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDatasets(); }, [fetchDatasets]);// vào trang dataset hàm fetch tự chạy

  const handleCreate = async (name: string, description?: string) => {
    await createDataset(name, description);
    await fetchDatasets();
  };

  const handleDeleteClick = async (e: React.MouseEvent, datasetId: string) => {
    e.stopPropagation();
    setCheckingUsage(true);
    try {
      const usage = await getDatasetUsage(datasetId);
      setDeleteUsage(usage);
      setDeleteTarget(datasetId);
    } catch {
      // fallback: show basic confirm without usage info
      setDeleteUsage(null);
      setDeleteTarget(datasetId);
    } finally {
      setCheckingUsage(false);
    }
  };

  const handleDeleteConfirmed = async () => {
    if (!deleteTarget) return;
    await deleteDataset(deleteTarget);
    setDeleteTarget(null);
    setDeleteUsage(null);
    await fetchDatasets();
  };

  const handleDeleteCancel = () => {
    setDeleteTarget(null);
    setDeleteUsage(null);
  };

  // Build warning message based on usage info
  const getDeleteMessage = (): string => {
    if (!deleteUsage) return t("deleteConfirm", "datasets");

    const hasDocuments = deleteUsage.document_count > 0;
    const linkedApps = deleteUsage.apps;

    if (!hasDocuments && linkedApps.length === 0) {
      return t("deleteConfirm", "datasets");
    }

    const parts: string[] = [];

    if (hasDocuments) {
      parts.push(
        t("deleteWarnDocuments", "datasets").replace("{count}", String(deleteUsage.document_count))
      );
    }

    if (linkedApps.length > 0) {
      const appNames = linkedApps.map((a) => `"${a.name}"`).join(", ");
      parts.push(t("deleteWarnApps", "datasets").replace("{apps}", appNames));
    }

    parts.push(t("deleteWarnConfirm", "datasets"));
    return parts.join(" ");
  };

  const isUsageWarning =
    !!deleteUsage &&
    (deleteUsage.document_count > 0 || deleteUsage.apps.length > 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div
          className="animate-spin rounded-full h-8 w-8 border-2 border-current"
          style={{ borderTopColor: "transparent", color: "var(--accent)" }}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="page-header flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-semibold" style={{ color: "var(--foreground)" }}>
            {t("title", "datasets")}
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            {t("description", "datasets")}
          </p>
        </div>
        <button
          id="btn-create-dataset"
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white transition-all duration-200"
          style={{ background: "var(--accent)" }}
          onMouseOver={(e) => { e.currentTarget.style.background = "var(--accent-hover)"; }}
          onMouseOut={(e) => { e.currentTarget.style.background = "var(--accent)"; }}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          {t("createDataset", "datasets")}
        </button>
      </div>

      {datasets.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center rounded-xl py-20"
          style={{ border: "1px dashed var(--border)", background: "var(--card)" }}
        >
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="mb-4">
            <rect x="8" y="8" width="32" height="32" rx="8" stroke="var(--muted)" strokeWidth="1.5" strokeDasharray="4 3" />
            <path d="M24 18V30M18 24H30" stroke="var(--muted)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <p className="text-sm font-medium" style={{ color: "var(--muted)" }}>
            {t("empty.title", "datasets")}
          </p>
          <p className="text-xs mt-1" style={{ color: "var(--muted)", opacity: 0.7 }}>
            {t("empty.description", "datasets")}
          </p>
        </div>
      ) : (
        <div
          className="responsive-table-wrap rounded-xl overflow-hidden"
          style={{ border: "1px solid var(--border)", background: "var(--card)" }}
        >
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)" }}>
                  {t("table.name", "datasets")}
                </th>
                <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)" }}>
                  {t("table.documents", "datasets")}
                </th>
                <th className="text-left px-4 py-3 font-medium" style={{ color: "var(--muted)" }}>
                  {t("table.created", "datasets")}
                </th>
                <th className="text-right px-4 py-3 font-medium" style={{ color: "var(--muted)" }}>
                  {t("table.actions", "datasets")}
                </th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((ds) => (
                <tr
                  key={ds.id}
                  className="transition-all duration-150 cursor-pointer"
                  style={{ borderBottom: "1px solid var(--border)" }}
                  onClick={() => router.push(`/datasets/${ds.id}`)}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "var(--card-hover)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}
                >
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium" style={{ color: "var(--foreground)" }}>{ds.name}</p>
                      {ds.description && (
                        <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{ds.description}</p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium"
                      style={{ background: "var(--accent-glow)", color: "var(--accent)" }}
                    >
                      {ds.document_count}
                    </span>
                  </td>
                  <td className="px-4 py-3" style={{ color: "var(--muted)" }}>
                    {new Date(ds.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      id={`btn-delete-dataset-${ds.id}`}
                      onClick={(e) => handleDeleteClick(e, ds.id)}
                      disabled={checkingUsage}
                      className="rounded-lg p-1.5 transition-all duration-200"
                      style={{ color: "var(--muted)" }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.color = "#ef4444";
                        e.currentTarget.style.background = "rgba(239,68,68,0.1)";
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.color = "var(--muted)";
                        e.currentTarget.style.background = "transparent";
                      }}
                    >
                      {checkingUsage ? (
                        <svg width="16" height="16" viewBox="0 0 16 16" className="animate-spin">
                          <circle
                            cx="8" cy="8" r="6"
                            stroke="currentColor" strokeWidth="1.5"
                            strokeDasharray="30" strokeDashoffset="10"
                            fill="none"
                          />
                        </svg>
                      ) : (
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                          <path
                            d="M3 4H13M5.5 4V3C5.5 2.44772 5.94772 2 6.5 2H9.5C10.0523 2 10.5 2.44772 10.5 3V4M6.5 7V11M9.5 7V11M4 4L4.5 13C4.5 13.5523 4.94772 14 5.5 14H10.5C11.0523 14 11.5 13.5523 11.5 13L12 4"
                            stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"
                          />
                        </svg>
                      )}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CreateDatasetModal
        open={showModal}
        onClose={() => setShowModal(false)}
        onCreate={handleCreate}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        title={
          isUsageWarning
            ? t("deleteWarnTitle", "datasets")
            : t("deleteConfirmTitle", "datasets")
        }
        message={getDeleteMessage()}
        confirmLabel={t("deleteConfirmBtn", "datasets")}
        variant="danger"
        onConfirm={handleDeleteConfirmed}
        onCancel={handleDeleteCancel}
      />
    </div>
  );
}
