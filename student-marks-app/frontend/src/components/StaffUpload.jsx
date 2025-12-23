import React, { useState, useEffect } from "react";
import { jwtDecode } from "jwt-decode";

/* ================= Utils ================= */

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let n = bytes;
  while (n >= 1024 && i < units.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(1)} ${units[i]}`;
}

function getToken() {
  return localStorage.getItem("token");
}

function decodeRole(token) {
  try {
    const d = jwtDecode(token);
    return d.role || "staff";
  } catch {
    return "staff";
  }
}

/* ================= Component ================= */

export default function StaffUpload({ token, setToken }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("staff");
  const [loginError, setLoginError] = useState("");

  const [file, setFile] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState("");
  const [loading, setLoading] = useState(false);

  const [uploads, setUploads] = useState([]);
  const [uploadsLoading, setUploadsLoading] = useState(false);
  const [uploadsError, setUploadsError] = useState("");

  const loggedIn = Boolean(token || getToken());
  const authToken = token || getToken();

  /* ---------- Init ---------- */
  useEffect(() => {
    if (!token && getToken()) setToken(getToken());
  }, [token, setToken]);

  useEffect(() => {
    if (authToken) {
      const r = decodeRole(authToken);
      setRole(r);
      if (r === "admin") fetchUploads(authToken);
    }
  }, [authToken]);

  /* ================= Auth ================= */

  async function handleLogin(e) {
    e.preventDefault();
    setLoginError("");
    setLoading(true);

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const j = await res.json();

      if (!res.ok) {
        setLoginError(j.error || "Login failed");
        return;
      }

      localStorage.setItem("token", j.token);
      setToken(j.token);
      setRole(decodeRole(j.token));
      setPassword("");
    } catch {
      setLoginError("Network error during login");
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("token");
    setToken("");
    setRole("staff");
    setUploads([]);
    setUploadResult(null);
    setFile(null);
  }

  /* ================= Upload ================= */

  async function handleUpload(e) {
    e.preventDefault();
    setUploadError("");
    setUploadResult(null);

    if (!file) {
      setUploadError("Please choose an Excel or CSV file.");
      return;
    }

    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);

      const res = await fetch("/api/upload-marks", {
        method: "POST",
        headers: { Authorization: `Bearer ${authToken}` },
        body: form
      });

      const j = await res.json();
      if (!res.ok) {
        setUploadError(j.error || "Upload failed");
        return;
      }

      setUploadResult(j);
      setFile(null);
      if (role === "admin") fetchUploads();
    } catch {
      setUploadError("Network error during upload");
    } finally {
      setLoading(false);
    }
  }

  /* ================= Admin APIs ================= */

  async function fetchUploads(t = authToken) {
    if (role !== "admin") return;
    setUploadsLoading(true);
    setUploadsError("");

    try {
      const res = await fetch("/api/admin/uploads", {
        headers: { Authorization: `Bearer ${t}` }
      });
      const j = await res.json();

      if (!res.ok) {
        setUploadsError(j.error || "Access denied");
        return;
      }

      setUploads(j.uploads || []);
    } catch {
      setUploadsError("Failed to fetch uploads");
    } finally {
      setUploadsLoading(false);
    }
  }

  async function handleDeleteFile(name) {
    if (!window.confirm(`Delete ${name}?`)) return;

    try {
      const res = await fetch("/api/admin/uploads", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`
        },
        body: JSON.stringify({ filename: name })
      });

      const j = await res.json();
      if (!res.ok) {
        setUploadsError(j.error || "Delete failed");
        return;
      }

      fetchUploads();
    } catch {
      setUploadsError("Delete failed");
    }
  }

  /* ================= UI ================= */

  return (
    <div className="center-wrap">
      <div className="card glass fade-in">

        {/* Header like Student Lookup */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h1 className="title" style={{ textAlign: "left" }}>
  Staff Upload
</h1>

          {loggedIn && (
            <button className="btn btn-ghost" onClick={handleLogout}>
              Logout
            </button>
          )}
        </div>

        {!loggedIn ? (
          <form onSubmit={handleLogin} className="form-grid" style={{ marginTop: 12 }}>
            <label>
              Email
              <input
                className="input"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="admin@example.com"
              />
            </label>

            <label>
              Password
              <input
                className="input"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </label>

            <button className="btn btn-primary" disabled={loading} style={{ marginTop: 12 }}>
              {loading ? "Logging in..." : "Login"}
            </button>

            {loginError && <div className="alert error">{loginError}</div>}
          </form>
        ) : (
          <>
            <div className="muted" style={{ marginBottom: 14 }}>
              Logged in as <b>{role}</b>
            </div>

            <form onSubmit={handleUpload} className="form-grid">
              <label>
                Upload Excel / CSV file
                <input
                  className="input"
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={e => setFile(e.target.files[0])}
                />
              </label>

              {file && (
                <div className="muted">
                  Selected: <b>{file.name}</b>
                </div>
              )}

              <button className="btn btn-primary" disabled={loading} style={{ marginTop: 12 }}>
                {loading ? "Uploading..." : "Upload"}
              </button>
            </form>

            {uploadError && <div className="alert error">{uploadError}</div>}

            {uploadResult && (
              <div className="resultBox">
                {JSON.stringify(uploadResult, null, 2)}
              </div>
            )}

            {/* ================= ADMIN PANEL ================= */}
            {role === "admin" && (
              <div style={{ marginTop: 32 }}>
                <h2>Uploaded files</h2>

                <div className="actions">
                  <button className="btn btn-ghost" onClick={() => fetchUploads()}>
                    Refresh
                  </button>
                </div>

                {uploadsError && <div className="alert error">{uploadsError}</div>}
                {uploadsLoading && <div className="muted">Loading...</div>}

                <table className="marks-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Size</th>
                      <th>Modified</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {uploads.map(f => (
                      <tr key={f.name}>
                        <td>{f.name}</td>
                        <td>{formatBytes(f.size_bytes)}</td>
                        <td>{new Date(f.modified_at).toLocaleString()}</td>
                        <td>
                          <button
                            className="btn btn-ghost"
                            onClick={() => handleDeleteFile(f.name)}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                    {uploads.length === 0 && (
                      <tr>
                        <td colSpan="4">No uploads found</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
