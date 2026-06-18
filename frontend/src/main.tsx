import React, { useEffect } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";

import { ErrorBoundary } from "./components/ErrorBoundary";
import { OfflineBanner } from "./components/OfflineBanner";
import { SyncButton } from "./components/SyncButton";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { AccountDetail } from "./pages/AccountDetail";
import { AccountList } from "./pages/AccountList";
import { AdminPanel } from "./pages/AdminPanel";
import { CalendarPage } from "./pages/CalendarPage";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { TurnList } from "./pages/TurnList";
import { ReportDashboard } from "./pages/ReportDashboard";
import { ReportBalance } from "./pages/ReportBalance";
import { ReportStatement } from "./pages/ReportStatement";
import { useSyncStore } from "./store/sync";
import { useCategoriesStore } from "./store/categories";
import "./style.css";

function RequireAuth({ children }: { children: JSX.Element }) {
  const { isLoggedIn } = useAuth();
  const location = useLocation();
  if (!isLoggedIn) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return children;
}

function Layout() {
  const { isLoggedIn, logout } = useAuth();
  const syncNow = useSyncStore((state) => state.syncNow);
  const fetchCategories = useCategoriesStore((state) => state.fetchCategories);

  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => {
        // ignore registration errors for now
      });
    }
    void syncNow();
    void fetchCategories();
    const handler = () => {
      void syncNow();
    };
    const interval = window.setInterval(() => {
      void syncNow();
    }, 5 * 60 * 1000);
    window.addEventListener("online", handler);
    return () => {
      window.removeEventListener("online", handler);
      window.clearInterval(interval);
    };
  }, [syncNow, fetchCategories]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div>
          <h1 className="brand">FerreGA Caja</h1>
          <p className="page-subtitle">Control contable en tiempo real.</p>
        </div>
        <ul className="nav-list">
          <li>
            <NavLink
              to="/home"
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              Inicio
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/accounts"
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              Cuentas
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/turn"
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              Turnos
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/calendar"
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              Calendario
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/report"
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              Reportes
            </NavLink>
          </li>
          <li>
            <NavLink
              to="/admin"
              className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
            >
              Administrador
            </NavLink>
          </li>
        </ul>
        <div className="sidebar-footer">
          {isLoggedIn ? (
            <button className="button button-ghost" type="button" onClick={logout}>
              Cerrar sesion
            </button>
          ) : (
            "Offline-first"
          )}
        </div>
      </aside>
      <main className="content">
        <div className="page-header">
          <div>
            <h2 className="page-title">Panel operativo</h2>
            <p className="page-subtitle">Tus datos siempre salen del backend.</p>
          </div>
          <SyncButton />
        </div>
        <OfflineBanner />
        <Routes>
          <Route path="/home" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/accounts" element={<AccountList />} />
          <Route path="/accounts/:id" element={<AccountDetail />} />
          <Route path="/turn" element={<TurnList />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/report" element={<ReportDashboard />} />
          <Route path="/report/balance" element={<ReportBalance />} />
          <Route path="/report/statement" element={<ReportStatement />} />
          <Route path="/admin" element={<AdminPanel />} />
          <Route path="/" element={<Navigate to="/home" replace />} />
          <Route path="*" element={<Navigate to="/home" replace />} />
        </Routes>
      </main>
    </div>
  );
}

// Asegurar que el contenedor #app exista
if (!document.getElementById("app")) {
  const div = document.createElement("div");
  div.id = "app";
  document.body.appendChild(div);
}

ReactDOM.createRoot(document.getElementById("app")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter>
          <Layout />
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
