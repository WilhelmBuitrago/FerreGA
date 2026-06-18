import { useEffect, useMemo } from "react";
import { useAccountStore } from "../store/accounts";

export function ReportBalance() {
  const accounts = useAccountStore((state) => state.accounts);
  const fetchAccounts = useAccountStore((state) => state.fetchAccounts);
  const loading = useAccountStore((state) => state.loading);

  useEffect(() => {
    void fetchAccounts();
  }, [fetchAccounts]);

  const assets = useMemo(() => {
    return accounts.filter(a => a.categoria === "ACTIVO" || !a.categoria || a.categoria === "ACTIVO");
  }, [accounts]);

  const liabilities = useMemo(() => {
    return accounts.filter(a => a.categoria === "PASIVO");
  }, [accounts]);

  const totalAssets = useMemo(() => assets.reduce((sum, a) => sum + a.account_amount, 0), [assets]);
  const totalLiabilities = useMemo(() => liabilities.reduce((sum, a) => sum + a.account_amount, 0), [liabilities]);
  const equity = totalAssets - totalLiabilities;

  const renderCascadingList = (title: string, items: typeof assets, total: number) => (
    <div style={{ marginBottom: 24 }}>
      <h3 style={{ fontSize: 16, marginBottom: 12 }}>{title}</h3>
      <div style={{ paddingLeft: 16 }}>
        {items.length === 0 ? (
          <div style={{ fontSize: 14, color: "var(--ink-500)", fontStyle: "italic" }}>No hay {title.toLowerCase()} registrados</div>
        ) : (
          items.map(a => (
            <div key={a.id} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0", fontSize: 14 }}>
              <span style={{ paddingLeft: 12 }}>{a.name}</span>
              <span>{a.account_amount.toFixed(2)}</span>
            </div>
          ))
        )}
        <div style={{ 
          marginTop: 6, 
          paddingTop: 6, 
          borderTop: "1px solid var(--border)",
          fontWeight: 600,
          display: "flex",
          justifyContent: "flex-end"
        }}>
          Total {title}: {total.toFixed(2)}
        </div>
      </div>
    </div>
  );

  return (
    <section className="card">
      <div className="page-header">
        <div>
          <h2 className="page-title">Balance General</h2>
          <p className="page-subtitle"> Estado de situación financiera</p>
        </div>
      </div>

      {loading ? (
        <p>Cargando cuentas...</p>
      ) : (
        <>
          {renderCascadingList("Activos", assets, totalAssets)}
          {renderCascadingList("Pasivos", liabilities, totalLiabilities)}
          
          <div style={{ borderTop: "2px solid var(--border)", paddingTop: 16 }}>
            <div style={{ fontSize: 18, fontWeight: 600, display: "flex", justifyContent: "space-between" }}>
              <span>Patrimonio (Activos - Pasivos)</span>
              <span style={{ color: equity >= 0 ? "#16a34a" : "#dc2626" }}>{equity.toFixed(2)}</span>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
