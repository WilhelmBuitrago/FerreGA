import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { CreateAccountModal } from "../components/CreateAccountModal";
import { useAccountStore } from "../store/accounts";

export function AccountList() {
  const navigate = useNavigate();
  const accounts = useAccountStore((state) => state.accounts);
  const loading = useAccountStore((state) => state.loading);
  const fetchAccounts = useAccountStore((state) => state.fetchAccounts);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    void fetchAccounts();
  }, [fetchAccounts]);

  return (
    <section className="card">
      <div className="page-header">
        <div>
          <h2 className="page-title">Cuentas activas</h2>
          <p className="page-subtitle">Balances calculados por el backend.</p>
        </div>
        <button className="button button-primary" type="button" onClick={() => setShowCreateModal(true)}>
          Nueva cuenta
        </button>
      </div>

      <CreateAccountModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={fetchAccounts}
      />

      <table className="table">
        <thead>
          <tr>
            <th>Cuenta</th>
            <th>Turno</th>
            <th>Saldo</th>
            <th>Diferencia</th>
            <th>Categoría</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <tr key={account.id} onClick={() => navigate(`/accounts/${account.id}`)}>
              <td>{account.name}</td>
              <td>{account.turn_amount.toFixed(2)}</td>
              <td>{account.account_amount.toFixed(2)}</td>
              <td>{account.difference.toFixed(2)}</td>
              <td>{account.categoria ?? "-"}</td>
            </tr>
          ))}
          {!accounts.length && !loading ? (
            <tr>
              <td colSpan={5}>No hay cuentas registradas.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </section>
  );
}