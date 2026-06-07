import { X, Radar, AlertTriangle, CheckCircle, Loader, FileUp } from "lucide-react";
import { useState } from "react";
import { importNmapXml, queueScan, ScanCreateResponse } from "../lib/api";

interface ScanModalProps {
  onClose: () => void;
}

type ModalState = "idle" | "loading" | "success" | "error";
type ScanMode = "institutional" | "external" | "xml_import";

// These IDs match the records inserted by seed_test_data.sql
const DEFAULT_POLICY_ID    = "c001e000-0000-0000-0000-000000000001";
const DEFAULT_PROFILE_ID   = "c002e000-0000-0000-0000-000000000001";
const DEFAULT_PROVIDER     = "nmap";

export function ScanModal({ onClose }: ScanModalProps): JSX.Element {
  const [targets, setTargets]     = useState<string>("");
  const [scanMode, setScanMode]   = useState<ScanMode>("institutional");
  const [engagementId, setEngagementId] = useState<string>("");
  const [xmlFile, setXmlFile] = useState<File | null>(null);
  const [xmlLabel, setXmlLabel] = useState<string>("xml-import");
  const [state, setState]         = useState<ModalState>("idle");
  const [result, setResult]       = useState<ScanCreateResponse | null>(null);
  const [errorMsg, setErrorMsg]   = useState<string>("");

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>): void {
    if (e.target === e.currentTarget) onClose();
  }

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();

    setState("loading");
    setErrorMsg("");

    try {
      let response: ScanCreateResponse;

      if (scanMode === "xml_import") {
        if (xmlFile === null) {
          throw new Error("Choose an Nmap XML file to import.");
        }
        const xmlContent = await xmlFile.text();
        response = await importNmapXml(xmlContent, xmlLabel.trim() || "xml-import");
      } else {
        const rawTargets = targets
          .split(/[\n,]+/)
          .map((t) => t.trim())
          .filter(Boolean);

        if (rawTargets.length === 0) {
          throw new Error("Enter at least one target.");
        }

        const trimmedEngagementId = engagementId.trim();
        if (scanMode === "external" && trimmedEngagementId.length === 0) {
          throw new Error("External engagement scans require an engagement ID.");
        }

        response = await queueScan({
          policy_id:          DEFAULT_POLICY_ID,
          scanner_profile_id: DEFAULT_PROFILE_ID,
          engagement_id:      scanMode === "external" ? trimmedEngagementId : null,
          provider:           DEFAULT_PROVIDER,
          scan_type:          "discovery",
          targets:            rawTargets,
        });
      }

      setResult(response);
      setState("success");
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : "Unknown error");
      setState("error");
    }
  }

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick} role="dialog" aria-modal="true" aria-label="Queue Scan">
      <div className="modal-card">
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title">
            <Radar aria-hidden="true" size={18} />
            <span>Queue Network Scan</span>
          </div>
          <button
            type="button"
            className="modal-close"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        {state === "success" && result ? (
          <div className="modal-body modal-result success">
            <CheckCircle size={40} aria-hidden="true" />
            <strong>Scan queued successfully</strong>
            <p className="modal-scan-id">ID: {result.scan_id}</p>
            <p className="modal-message">{result.message}</p>
            <button type="button" className="modal-btn primary" onClick={onClose}>
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} noValidate>
            <div className="modal-body">
              <div className="scan-mode-row" role="tablist" aria-label="Scan mode">
                <button
                  type="button"
                  className={`scan-mode-btn${scanMode === "institutional" ? " active" : ""}`}
                  onClick={() => setScanMode("institutional")}
                  disabled={state === "loading"}
                >
                  Institutional
                </button>
                <button
                  type="button"
                  className={`scan-mode-btn${scanMode === "external" ? " active" : ""}`}
                  onClick={() => setScanMode("external")}
                  disabled={state === "loading"}
                >
                  External
                </button>
                <button
                  type="button"
                  className={`scan-mode-btn${scanMode === "xml_import" ? " active" : ""}`}
                  onClick={() => setScanMode("xml_import")}
                  disabled={state === "loading"}
                >
                  XML Import
                </button>
              </div>

              {scanMode === "xml_import" ? (
                <>
                  <label className="modal-label" htmlFor="xml-label">
                    Import label
                    <span className="modal-hint">Used to identify the uploaded Nmap artifact.</span>
                  </label>
                  <input
                    id="xml-label"
                    className="modal-input"
                    value={xmlLabel}
                    onChange={(e) => setXmlLabel(e.target.value)}
                    disabled={state === "loading"}
                  />

                  <label className="modal-label" htmlFor="xml-file">
                    Nmap XML file
                    <span className="modal-hint">No live probes are sent; hosts are ingested from the artifact.</span>
                  </label>
                  <input
                    id="xml-file"
                    className="modal-input"
                    type="file"
                    accept=".xml,application/xml,text/xml"
                    onChange={(e) => setXmlFile(e.target.files?.[0] ?? null)}
                    disabled={state === "loading"}
                    required
                  />
                </>
              ) : (
                <>
                  {scanMode === "external" && (
                    <>
                      <label className="modal-label" htmlFor="engagement-id">
                        Engagement ID
                        <span className="modal-hint">Required for external scans; backend enforces authorized scope.</span>
                      </label>
                      <input
                        id="engagement-id"
                        className="modal-input"
                        placeholder="00000000-0000-0000-0000-000000000000"
                        value={engagementId}
                        onChange={(e) => setEngagementId(e.target.value)}
                        disabled={state === "loading"}
                        required
                      />
                    </>
                  )}

                  <label className="modal-label" htmlFor="scan-targets">
                    Targets
                    <span className="modal-hint">
                      Institutional scans allow RFC1918/VPC/public targets. External scans allow public targets only.
                    </span>
                  </label>
                  <textarea
                    id="scan-targets"
                    className="modal-textarea"
                    placeholder={"192.168.1.0/24\n10.0.0.1\n8.8.8.8"}
                    value={targets}
                    onChange={(e) => setTargets(e.target.value)}
                    rows={5}
                    disabled={state === "loading"}
                    required
                    autoFocus
                  />
                </>
              )}

              <div className="modal-meta-grid">
                <div className="modal-meta-item">
                  <span className="modal-meta-label">Mode</span>
                  <span className="modal-meta-value">{scanMode.replace("_", " ")}</span>
                </div>
                <div className="modal-meta-item">
                  <span className="modal-meta-label">Provider</span>
                  <span className="modal-meta-value">nmap</span>
                </div>
                <div className="modal-meta-item">
                  <span className="modal-meta-label">Validation</span>
                  <span className="modal-meta-value">
                    {scanMode === "xml_import" ? "artifact" : scanMode === "external" ? "public + scope" : "institutional"}
                  </span>
                </div>
              </div>

              {state === "error" && (
                <div className="modal-error" role="alert">
                  <AlertTriangle size={15} aria-hidden="true" />
                  <span>{errorMsg}</span>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="modal-btn secondary"
                onClick={onClose}
                disabled={state === "loading"}
              >
                Cancel
              </button>
              <button
                type="submit"
                id="scan-submit"
                className="modal-btn primary"
                disabled={
                  state === "loading" ||
                  (scanMode === "xml_import" ? xmlFile === null : targets.trim() === "")
                }
              >
                {state === "loading" ? (
                  <>
                    <Loader size={14} className="spin" aria-hidden="true" />
                    Queuing…
                  </>
                ) : (
                  <>
                    {scanMode === "xml_import" ? <FileUp size={14} aria-hidden="true" /> : <Radar size={14} aria-hidden="true" />}
                    {scanMode === "xml_import" ? "Import XML" : "Queue Scan"}
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
