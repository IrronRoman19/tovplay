import { useState } from "react";
import { Link } from "react-router-dom";
import { apiService } from "@/api/apiService";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");

    try {
      await apiService.requestPasswordReset(email.trim().toLowerCase());
      setMessage(
        "If an account with that email exists, a password reset link has been sent."
      );
    } catch {
      setError("Something went wrong. Please try again later.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <h2>Reset your password</h2>

      <form onSubmit={handleSubmit}>
        <label>Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <button type="submit" disabled={loading || !email}>
          {loading ? "Sending..." : "Send reset link"}
        </button>
      </form>

      {message && <p className="success-text">{message}</p>}
      {error && <p className="error-text">{error}</p>}

      <Link to="/SignIn">Back to sign in</Link>
    </div>
  );
}
