import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../lib/api";
import { ActionHistory } from "../components/ActionHistory";
import { useAccountStore } from "../store/accounts";
import { notifyError } from "../ui/toast";

interface TurnGroup {
  turn_group_id: string;
  status: "OPEN" | "CLOSED";
  opened_at: string;
  closed_at: string | null;
  account_count: number;
}

interface TurnGroupListResponse {
  groups: TurnGroup[];
}

interface TurnSummary {
  turn_group_id: string;
  status: string;
  opened_at: string;
  liquidity: number;
  incomes: number;
  expenses: number;
  turn_devengo: number;
  turn_cxc: number;
  turn_cxp: number;
}

export function TurnList() {
  const navigate = useNavigate();
  const accounts = useAccountStore((state) => state.accounts);
  const [groups, setGroups] = useState<TurnGroup[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [summary, setSummary] = useState<TurnSummary | null>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<string>("");

  useEffect(() => {
    void fetchGroups();
  }, []);

  useEffect(() => {
    if (selectedGroupId) {
      void fetchSummary();
    }
  }, [selectedGroupId, selectedAccountId]);

  const fetchGroups = async () => {
    setLoading(true);
    try {
      const response = await api.get<TurnGroupListResponse>("/turns/groups");
      setGroups(response.data.groups);
    } catch (error) {
      console.error("Error loading turn groups", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    if (!selectedGroupId) return;
    try {
      const params: any = {};
      if (selectedAccountId) params.account_id = selectedAccountId;
      const response = await api.get<TurnSummary>(`/turns/group/${selectedGroupId}/summary`, { params });
      const data = response.data;
      // Convertir campos numéricos a Number
      setSummary({
        ...data,
        liquidity: Number(data.liquidity),
        incomes: Number(data.incomes),
        expenses: Number(data.expenses),
        turn_devengo: Number(data.turn_devengo),
        turn_cxc: Number(data.turn_cxc),
        turn_cxp: Number(data.turn_cxp),
      });
    } catch (error) {
      console.error("Error loading turn summary", error);
      notifyError("No se pudo cargar el resumen del turno");
    }
  };

  if (selectedGroupId) {
    return (
      <div>
        <button className="button button-ghost" type="button" onClick={() => setSelectedGroupId(null)}>
          ← Volver a lista de turnos
        </button>

        <h2 className="page-title" style={{ marginTop: "16px" }}>
          Detalle de turno {selectedGroupId.slice(0, 8)}...
        </h2>

        {summary && (
          <div className="metric-grid" style={{ marginTop: 16, gridTemplateColumns: "repeat(2, 1fr)" }}>
            <div className="metric metric-liquidity" style={{ gridColumn: "span 2" }}>
              <div className="metric-label">Liquidez</div>
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
              <div className="metric-label">Cuentas por Cobrar</div>
              <div className="metric-value">{summary.turn_cxc.toFixed(2)}</div>
            </div>
            <div className="metric metric-cxp">
              <div className="metric-label">Cuentas por Pagar</div>
              <div className="metric-value">{summary.turn_cxp.toFixed(2)}</div>
            </div>
          </div>
        )}

        <div style={{ marginTop: 16 }}>
          <label style={{ marginRight: 8 }}>Filtrar por cuenta:</label>
          <select
            value={selectedAccountId}
            onChange={(e) => setSelectedAccountId(e.target.value)}
            style={{ padding: 4, width: 200 }}
          >
            <option value="">Todas las cuentas</option>
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.id}>{acc.name}</option>
            ))}
          </select>
        </div>

        <ActionHistory
          turnGroupId={selectedGroupId}
          accountId={selectedAccountId || undefined}
        />
      </div>
    );
  }

  return (
    <section className="card">
      <h2 className="page-title">Historial de turnos</h2>
      <p className="page-subtitle">Todos los turnos globales (pasados y actuales)</p>
      {loading ? (
        <p>Cargando...</p>
      ) : groups.length === 0 ? (
        <p>No hay turnos registrados.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>ID Turno</th>
              <th>Estado</th>
              <th>Apertura</th>
              <th>Cierre</th>
              <th>Cuentas</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => (
              <tr key={group.turn_group_id}>
                <td>{group.turn_group_id.slice(0, 8)}...</td>
                <td>{group.status}</td>
                <td>{new Date(group.opened_at).toLocaleString("es-ES")}</td>
                <td>{group.closed_at ? new Date(group.closed_at).toLocaleString("es-ES") : "-"}</td>
                <td>{group.account_count}</td>
                <td>
                  <button className="button button-primary" type="button" onClick={() => setSelectedGroupId(group.turn_group_id)}>
                    Ver historial
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
