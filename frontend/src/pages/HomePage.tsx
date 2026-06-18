import { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { ActionHistory } from "../components/ActionHistory";
import { FloatingActionMenu } from "../components/FloatingActionMenu";
import { useAccountStore } from "../store/accounts";
import { useTurnStore } from "../store/turns";
import { useMovementStore } from "../store/movements";

interface HistoricalSummary {
  liquidity: number;
  incomes: number;
  expenses: number;
  turn_cxc: number;
  turn_cxp: number;
}

export function HomePage() {
  const [summary, setSummary] = useState<HistoricalSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const activeGlobal = useTurnStore((state) => state.activeGlobal);
  const fetchActiveGlobal = useTurnStore((state) => state.fetchActiveGlobal);
  const fetchAccounts = useAccountStore((state) => state.fetchAccounts);
  const lastMovementUpdate = useMovementStore((state) => state.lastUpdate);

  const fetchSummary = useCallback(async () => {
    setLoading(true);
    try {
      let data;
      if (activeGlobal?.turn_group_id) {
        // Resumen del turno activo
        const res = await api.get(`/turns/group/${activeGlobal.turn_group_id}/summary`);
        data = res.data;
      } else {
        // Resumen histórico
        const res = await api.get("/turns/summary/historical");
        data = res.data;
      }
      setSummary(data);
    } catch (e) {
      console.error("Error loading summary", e);
    } finally {
      setLoading(false);
    }
  }, [activeGlobal?.turn_group_id]);

  useEffect(() => {
    void fetchActiveGlobal();
    void fetchAccounts();
  }, [fetchActiveGlobal, fetchAccounts]);

  useEffect(() => {
    void fetchSummary();
  }, [fetchSummary, lastMovementUpdate]);

  return (
    <section className="card">
      <div className="page-header">
        <div>
          <h2 className="page-title">Inicio</h2>
          <p className="page-subtitle">Resumen de la aplicación.</p>
        </div>
      </div>

      {loading ? (
        <p>Cargando resumen...</p>
      ) : summary ? (
        <div className="metric-grid" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
          <div className="metric metric-liquidity" style={{ gridColumn: "span 2" }}>
            <div className="metric-label">Liquidez total</div>
            <div className="metric-value">{summary.liquidity.toFixed(2)}</div>
          </div>
          <div className="metric metric-income">
            <div className="metric-label">Ingresos</div>
            <div className="metric-value">{summary.incomes.toFixed(2)}</div>
          </div>
          <div className="metric metric-expense">
            <div className="metric-label">Egresos</div>
            <div className="metric-value">{summary.expenses.toFixed(2)}</div>
          </div>
          <div className="metric metric-cxc">
            <div className="metric-label">Cuentas por cobrar</div>
            <div className="metric-value">{summary.turn_cxc.toFixed(2)}</div>
          </div>
          <div className="metric metric-cxp">
            <div className="metric-label">Cuentas por pagar</div>
            <div className="metric-value">{summary.turn_cxp.toFixed(2)}</div>
          </div>
        </div>
      ) : (
        <p>No se pudo cargar el resumen.</p>
      )}

       <ActionHistory turnGroupId={activeGlobal?.turn_group_id} />
      <FloatingActionMenu activeTurnStatus={activeGlobal?.status ?? "CLOSED"} />
    </section>
  );
}
