import React, { useState } from "react";
import { Eye, EyeOff, Lock, Mail, Shield, User } from "lucide-react";
import { loginUser, registerUser } from "../lib/api";

interface AuthViewProps {
  onAuthSuccess: (token: string, userInfo: { email: string; display_name: string; roles: string[] }) => void;
  onBypass: () => void;
}

export function AuthView({ onAuthSuccess, onBypass }: AuthViewProps): JSX.Element {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (isRegister) {
        if (password.length < 6) {
          throw new Error("Password must be at least 6 characters long.");
        }
        if (displayName.trim().length < 2) {
          throw new Error("Display name must be at least 2 characters.");
        }
        const data = await registerUser(email, password, displayName);
        onAuthSuccess(data.access_token, {
          email: data.email,
          display_name: data.display_name,
          roles: data.roles,
        });
      } else {
        const data = await loginUser(email, password);
        onAuthSuccess(data.access_token, {
          email: data.email,
          display_name: data.display_name,
          roles: data.roles,
        });
      }
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-overlay">
      <div className="auth-container">
        {/* Animated Cyber Glows */}
        <div className="auth-glow auth-glow-1"></div>
        <div className="auth-glow auth-glow-2"></div>

        <div className="auth-card">
          <div className="auth-header">
            <div className="auth-logo">
              <Shield size={38} className="logo-icon" />
              <h1>Sentinel AI</h1>
            </div>
            <p className="auth-subtitle">
              {isRegister ? "Create analyst credentials to access the node" : "Security Operations Center Portal"}
            </p>
          </div>

          {error && (
            <div className="auth-error-banner" role="alert">
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form">
            {isRegister && (
              <div className="auth-input-group">
                <label htmlFor="displayName">Display Name</label>
                <div className="auth-input-wrapper">
                  <User size={18} className="auth-input-icon" />
                  <input
                    id="displayName"
                    type="text"
                    placeholder="Analyst Name"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    required
                    disabled={loading}
                    autoComplete="name"
                  />
                </div>
              </div>
            )}

            <div className="auth-input-group">
              <label htmlFor="email">Email Address</label>
              <div className="auth-input-wrapper">
                <Mail size={18} className="auth-input-icon" />
                <input
                  id="email"
                  type="email"
                  placeholder="analyst@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={loading}
                  autoComplete="email"
                />
              </div>
            </div>

            <div className="auth-input-group">
              <label htmlFor="password">Access Password</label>
              <div className="auth-input-wrapper">
                <Lock size={18} className="auth-input-icon" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={loading}
                  autoComplete={isRegister ? "new-password" : "current-password"}
                />
                <button
                  type="button"
                  className="auth-password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  disabled={loading}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button type="submit" className="auth-submit-btn" disabled={loading}>
              {loading ? (
                <div className="auth-spinner"></div>
              ) : isRegister ? (
                "Initialize Credentials"
              ) : (
                "Authorize Access"
              )}
            </button>
          </form>

          <div className="auth-footer">
            <button
              type="button"
              className="auth-switch-mode-btn"
              onClick={() => {
                setIsRegister(!isRegister);
                setError(null);
                setPassword("");
              }}
              disabled={loading}
            >
              {isRegister ? "Already registered? Authenticate here" : "Need credentials? Register new analyst"}
            </button>

            <div className="auth-divider">
              <span>OR</span>
            </div>

            <button type="button" className="auth-bypass-btn" onClick={onBypass} disabled={loading}>
              Bypass Authentication (Development Mode)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
