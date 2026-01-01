import { useEffect, useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import { apiService } from "@/api/apiService";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [validating, setValidating] = useState(true);

  useEffect(() => {
    const validateToken = async () => {
      if (!token) {
        setError("Invalid or missing reset token.");
        setValidating(false);
        return;
      }

      try {
        await apiService.validateResetToken(token);
        setValidating(false);
      } catch {
        setError("Reset link is invalid or expired.");
        setValidating(false);
      }
    };

    validateToken();
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await apiService.resetPassword({
        token,
        password,
        confirm_password: confirmPassword
      });
      navigate("/SignIn");
    } catch {
      setError("Reset link is invalid or expired.");
    } finally {
      setLoading(false);
    }
  };

  if (validating) {
    return <div className="auth-container">Validating reset link…</div>;
  }

  if (error && !token) {
    return (
      <div className="auth-container">
        <p>{error}</p>
        <Link to="/SignIn">Back to sign in</Link>
      </div>
    );
  }

  return (
    <div className="auth-container">
      <h2>Set a new password</h2>

      <form onSubmit={handleSubmit}>
        <label>New password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <label>Confirm password</label>
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />

        <button type="submit" disabled={loading}>
          {loading ? "Resetting…" : "Reset password"}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}
    </div>
  );
}
