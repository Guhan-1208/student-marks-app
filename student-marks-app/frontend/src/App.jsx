import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import { jwtDecode } from "jwt-decode";


import StudentLookup from "./components/StudentLookup";
import StaffUpload from "./components/StaffUpload";

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [role, setRole] = useState("");

  // Decode role whenever token changes
  useEffect(() => {
    if (!token) {
      setRole("");
      return;
    }
    try {
      const decoded = jwtDecode(token);
      setRole(decoded.role || "");
    } catch {
      setRole("");
    }
  }, [token]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken("");
    setRole("");
  };

  return (
    <Router>
      <div className="app-root">
        {/* ================= HEADER ================= */}
        <header className="topbar">
          <div className="topbar-inner">
            <div className="brand">Student Marks</div>

            <nav className="nav">
              <Link className="nav-link" to="/">Student Lookup</Link>
              <Link className="nav-link" to="/upload">Staff Upload</Link>
            </nav>

            <div className="right" style={{ marginLeft: "auto" }}>
              {token && (
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <span className="muted" style={{ fontSize: 14 }}>
                    {role && `Logged in as ${role}`}
                  </span>
                  <button className="btn btn-ghost" onClick={handleLogout}>
                    Logout
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* ================= CONTENT ================= */}
        <main className="page">
          <Routes>
            <Route path="/" element={<StudentLookup />} />
            <Route
              path="/upload"
              element={
                <StaffUpload
                  token={token}
                  setToken={setToken}
                  onLogout={handleLogout}
                />
              }
            />
          </Routes>
        </main>

        {/* ================= FOOTER ================= */}
        <footer className="footer">
          <div>© {new Date().getFullYear()} Student Marks</div>
        </footer>
      </div>
    </Router>
  );
}
