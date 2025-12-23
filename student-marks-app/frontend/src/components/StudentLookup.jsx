import React, { useState, useRef } from "react";

/* Helpers */

function formatDobAuto(input) {
  const digits = input.replace(/\D/g, "").slice(0, 8);
  if (digits.length <= 2) return digits;
  if (digits.length <= 4) return `${digits.slice(0, 2)}-${digits.slice(2)}`;
  return `${digits.slice(0, 2)}-${digits.slice(2, 4)}-${digits.slice(4)}`;
}

function isValidDobString(ddmmyyyy) {
  if (!/^\d{2}-\d{2}-\d{4}$/.test(ddmmyyyy)) return false;
  const [dd, mm, yyyy] = ddmmyyyy.split("-").map(Number);
  if (mm < 1 || mm > 12) return false;
  if (dd < 1 || dd > 31) return false;
  const thirtyDays = [4, 6, 9, 11];
  if (thirtyDays.includes(mm) && dd > 30) return false;
  if (mm === 2) {
    const isLeap = (yyyy % 4 === 0 && yyyy % 100 !== 0) || (yyyy % 400 === 0);
    if (isLeap && dd > 29) return false;
    if (!isLeap && dd > 28) return false;
  }
  if (yyyy < 1900 || yyyy > new Date().getFullYear()) return false;
  return true;
}

function convertDDMMYYYYtoISO(ddmmyyyy) {
  const [dd, mm, yyyy] = ddmmyyyy.split("-");
  return `${yyyy}-${mm}-${dd}`;
}

export default function StudentLookup() {
  const [registerNumber, setRegisterNumber] = useState("");
  const [dob, setDob] = useState("");
  const [loading, setLoading] = useState(false);
  const [marks, setMarks] = useState(null);
  const [studentName, setStudentName] = useState("");
  const [error, setError] = useState("");
  const [isResultsVisible, setIsResultsVisible] = useState(false);

  const clearTimerRef = useRef(null);

  function clearResultsAnimated() {
    if (!isResultsVisible) {
      setMarks(null);
      setStudentName("");
      setError("");
      return;
    }
    setIsResultsVisible(false);
    clearTimeout(clearTimerRef.current);
    clearTimerRef.current = setTimeout(() => {
      setMarks(null);
      setStudentName("");
      setError("");
    }, 320);
  }

  function handleRegChange(e) {
    setRegisterNumber(e.target.value);
    setError("");
    clearResultsAnimated();
  }

  function handleDobChange(e) {
    const formatted = formatDobAuto(e.target.value);
    setDob(formatted);
    setError("");
    clearResultsAnimated();
  }

  function handleReset() {
    setRegisterNumber("");
    setDob("");
    setError("");
    clearResultsAnimated();
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    clearTimeout(clearTimerRef.current);

    if (!registerNumber.trim() || !dob.trim()) {
      setError("Please enter both Register Number and Date of Birth.");
      clearResultsAnimated();
      return;
    }

    if (!isValidDobString(dob.trim())) {
      setError("DOB must be a valid date in DD-MM-YYYY format.");
      clearResultsAnimated();
      return;
    }

    const isoDob = convertDDMMYYYYtoISO(dob.trim());
    setLoading(true);

    try {
      const res = await fetch("/api/students/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          register_number: registerNumber.trim(),
          dob: isoDob
        })
      });

      const data = await res.json();
      if (!res.ok) {
        setError(data.error || "Failed to fetch marks. Try again.");
        clearResultsAnimated();
      } else {
        setMarks(data.marks || []);
        setStudentName(data.student_name || "");
        setTimeout(() => setIsResultsVisible(true), 10);
      }
    } catch (err) {
      console.error(err);
      setError("Network error. Make sure the backend is running.");
      clearResultsAnimated();
    } finally {
      setLoading(false);
    }
  }

  const isFormValid =
    registerNumber.trim() !== "" && isValidDobString(dob.trim());

  return (
    <div className="center-wrap">
      <div className="card glass fade-in">
        <div style={{ display: "flex", alignItems: "center", gap: 12, justifyContent: "space-between" }}>
          <h1 className="title">Student Lookup</h1>
          <button className="btn btn-ghost" type="button" onClick={handleReset}>
            Reset
          </button>
        </div>

        <form onSubmit={handleSubmit} className="form-grid" style={{ marginTop: 8 }}>
          <label className="label">
            Register Number
            <input
              className="input"
              value={registerNumber}
              onChange={handleRegChange}
              placeholder="e.g. 421622205001"
              disabled={loading}
            />
          </label>

          <label className="label">
            Date of Birth (DD-MM-YYYY)
            <input
              className="input"
              value={dob}
              onChange={handleDobChange}
              placeholder="12-03-2005"
              inputMode="numeric"
              disabled={loading}
            />
            <small style={{ color: "#9aa4b2", marginTop: 6 }}>
              Type digits; dashes are inserted automatically.
            </small>
          </label>

          <div className="actions">
            <button className="btn btn-primary" disabled={!isFormValid || loading}>
              {loading ? "Checking..." : "View Marks"}
            </button>
          </div>
        </form>

        {error && <div className="alert error" style={{ marginTop: 12 }}>{error}</div>}

        {marks && (
          <div
            className={`results ${isResultsVisible ? "fade-in-up" : "fade-out"}`}
            style={{ marginTop: 12, transition: "all .32s ease" }}
          >
            <h3>
              {studentName
                ? `${studentName} — ${registerNumber}`
                : `Marks for ${registerNumber}`}
            </h3>

            {marks.length === 0 ? (
              <div className="muted">No marks found for this student.</div>
            ) : (
              <table className="marks-table">
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th>Marks</th>
                    <th>Uploaded By</th>
                    <th>Uploaded At</th>
                  </tr>
                </thead>
                <tbody>
                  {marks.map((m, idx) => (
                    <tr key={idx}>
                      <td>{m.subject_code || m.subject_name || "-"}</td>
                      <td>{m.marks}</td>
                      <td>{m.uploaded_by || "-"}</td>
                      <td>{m.uploaded_at ? new Date(m.uploaded_at).toLocaleString() : "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
