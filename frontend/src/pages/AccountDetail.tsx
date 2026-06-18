import { useEffect } from "react";
import { useParams } from "react-router-dom";

import { useAccountStore } from "../store/accounts";
import { useTurnStore } from "../store/turns";
import { ActionHistory } from "../components/ActionHistory";

export function AccountDetail() {
  const { id } = useParams();
  const fetchAccountDetail = useAccountStore((state) => state.fetchAccountDetail);
  const account = useAccountStore((state) => state.selected);
  const activeGlobal = useTurnStore((state) => state.activeGlobal);

  useEffect(() => {
    if (id) {
      void fetchAccountDetail(id);
    }
  }, [id, fetchAccountDetail]);

  if (!id) return null;

  if (!account) {
    return (
      <section className="card">
        <h2 className="page-title">Cargando cuenta...</h2>
      </section>
    );
  }

  return (
    <section className="card">
      <div className="page-header">
        <div>
          <h2 className="page-title">Detalle de cuenta</h2>
          <p className="page-subtitle">{account.name}</p>
        </div>
      </div>

      <div className="metric-grid" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
        <div className="metric metric-liquidity" style={{ gridColumn: "span 2" }}>
          <div className="metric-label">Liquidez</div>
          <div className="metric-value">{account.liquidity.toFixed(2)}</div>
        </div>
        <div className="metric metric-income">
          <div className="metric-label">Ingresos</div>
          <div className="metric-value">{account.incomes.toFixed(2)}</div>
        </div>
        <div className="metric metric-expense">
          <div className="metric-label">Egresos</div>
          <div className="metric-value">{account.expenses.toFixed(2)}</div>
        </div>
      </div>

      <ActionHistory turnGroupId={activeGlobal?.turn_group_id} accountId={id} />
    </section>
  );
}