import { X, Radar, AlertTriangle, CheckCircle, Loader } from "lucide-react";
import { useState } from "react";
import { queueScan, ScanCreateResponse } from "../lib/api";

interface ScanModalProps {
  onClose: () => void;
}

type ModalState = "idle" | "loading" | "success" | "error";

// These IDs match the records inserted by seed_test_data.sql
const DEFAULT_POLICY_ID    = "c001e000-0000-0000-0000-000000000001";
const DEFAULT_PROFILE_ID   = "c002e000-0000-0000-0000-000000000001";
const DEFAULT_PROVIDER     = "nmap";

export function ScanModal({ onClose }: ScanModalProps): JSX.Element {
  const [targets, setTargets]     = useState<string>("");
  const [state, setState]         = useState<ModalState>("idle");
  const [result, setResult]       = useState<ScanCreateResponse | null>(null);
  const [errorMsg, setErrorMsg]   = useState<string>("");

  function handleBackdropClick(e: React.MouseEvent<HTMLDivElement>): void {
    if (e.target === e.currentTarget) onClose();
  }

  async function handleSubmit(e: React.FormEvent): Promise<void> {
    e.preventDefault();
    const rawTargets = targets
      .split(/[\n,]+/)
      .map((t) => t.trim())
      .filter(Boolean);

    if (rawTargets.length === 0) return;

    setState("loading");
    setErrorMsg("");

    try {
      const response = await queueScan({
        policy_id:          DEFAULT_POLICY_ID,
        scanner_profile_id: DEFAULT_PROFILE_ID,
        provider:           DEFAULT_PROVIDER,
        scan_type:          "discovery",
        targets:            rawTargets,
      });
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
              <label className="modal-label" htmlFor="scan-targets">
                Targets
                <span className="modal-hint">
                  One per line or comma-separated. Allowed ranges: <code>127.0.0.0/8</code>, <code>10.0.0.0/8</code>, <code>192.168.0.0/16</code>.
                </span>
              </label>
              <textarea
                id="scan-targets"
                className="modal-textarea"
                placeholder={"192.168.1.0/24\n10.0.0.1\n127.0.0.1"}
                value={targets}
                onChange={(e) => setTargets(e.target.value)}
                rows={5}
                disabled={state === "loading"}
                required
                autoFocus
              />

              <div className="modal-meta-grid">
                <div className="modal-meta-item">
                  <span className="modal-meta-label">Provider</span>
                  <span className="modal-meta-value">nmap</span>
                </div>
                <div className="modal-meta-item">
                  <span className="modal-meta-label">Scan Type</span>
                  <span className="modal-meta-value">discovery</span>
                </div>
                <div className="modal-meta-item">
                  <span className="modal-meta-label">Auth</span>
                  <span className="modal-meta-value">dev-analyst</span>
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
                disabled={state === "loading" || targets.trim() === ""}
              >
                {state === "loading" ? (
                  <>
                    <Loader size={14} className="spin" aria-hidden="true" />
                    Queuing…
                  </>
                ) : (
                  "Queue Scan"
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
