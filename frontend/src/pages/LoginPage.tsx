import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { api, parseApiError } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";
import { notifyError } from "../ui/toast";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!username.trim() || !password.trim()) return;
    setLoading(true);
    try {
      const response = await api.post<{ access_token: string }>("/auth/login", {
        username: username.trim(),
        password: password.trim(),
      });
      login(response.data.access_token);
      const redirectTo = (location.state as { from?: string } | null)?.from ?? "/home";
      navigate(redirectTo, { replace: true });
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card">
      <div>
        <h2 className="page-title">Acceso administrador</h2>
        <p className="page-subtitle">Ingresa con tus credenciales para continuar.</p>
      </div>
      <div className="form-grid">
        <label>
          Usuario
          <input value={username} onChange={(event) => setUsername(event.target.value)} />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
      </div>
      <div className="modal-actions">
        <button className="button button-primary" type="button" onClick={handleSubmit} disabled={loading}>
          Ingresar
        </button>
      </div>
    </section>
  );
}
