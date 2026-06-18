import { useEffect, useState } from "react";

import { ConfirmModal } from "../components/ConfirmModal";
import { useAccountStore } from "../store/accounts";
import type { AccountSummary } from "../store/accounts";

export function AdminAccounts() {
  const accounts = useAccountStore((state) => state.accounts);
  const loading = useAccountStore((state) => state.loading);
  const fetchAccounts = useAccountStore((state) => state.fetchAccounts);
  const updateAccount = useAccountStore((state) => state.updateAccount);
  const deleteAccount = useAccountStore((state) => state.deleteAccount);
  const [editing, setEditing] = useState<AccountSummary | null>(null);
  const [editName, setEditName] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<AccountSummary | null>(null);

  useEffect(() => {
    void fetchAccounts(true);
  }, [fetchAccounts]);

  const openEdit = (account: AccountSummary) => {
    setEditing(account);
    setEditName(account.name);
    setEditAmount(account.account_amount.toFixed(2));
  };

  const closeEdit = () => {
    setEditing(null);
    setEditName("");
    setEditAmount("");
  };

  const handleSave = async () => {
    if (!editing) return;
    const trimmedName = editName.trim();
    const amountValue = editAmount.trim() ? Number(editAmount) : null;
    await updateAccount(
      editing.id,
      {
        name: trimmedName ? trimmedName : undefined,
        account_amount: Number.isNaN(amountValue) ? null : amountValue,
      },
      true
    );
    closeEdit();
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    const hasBalance = deleteTarget.turn_amount !== 0 || deleteTarget.account_amount !== 0;
    await deleteAccount(deleteTarget.id, { force: hasBalance, includeInactive: true });
    setDeleteTarget(null);
  };

  return (
    <section className="card">
      <div className="page-header">
        <div>
          <h3>Cuentas</h3>
          <p className="page-subtitle">Administra nombre, monto y elimina cuentas.</p>
        </div>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Cuenta</th>
            <th>Turno</th>
            <th>Cuenta</th>
            <th>Diferencia</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <tr key={account.id}>
              <td>{account.name}</td>
              <td>{account.turn_amount.toFixed(2)}</td>
              <td>{account.account_amount.toFixed(2)}</td>
              <td>{account.difference.toFixed(2)}</td>
              <td>
                <div className="modal-actions">
                  <button className="button button-ghost" type="button" onClick={() => openEdit(account)}>
                    Editar
                  </button>
                  <button className="button button-secondary" type="button" onClick={() => setDeleteTarget(account)}>
                    Eliminar
                  </button>
                </div>
              </td>
            </tr>
          ))}
          {!accounts.length && !loading ? (
            <tr>
              <td colSpan={5}>No hay cuentas registradas.</td>
            </tr>
          ) : null}
        </tbody>
      </table>

      {editing ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <h3>Editar cuenta</h3>
            <div className="form-grid">
              <label>
                Nombre
                <input value={editName} onChange={(event) => setEditName(event.target.value)} />
              </label>
              <label>
                Monto
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={editAmount}
                  onChange={(event) => setEditAmount(event.target.value)}
                />
              </label>
            </div>
            <div className="modal-actions">
              <button className="button button-ghost" type="button" onClick={closeEdit}>
                Cancelar
              </button>
              <button className="button button-primary" type="button" onClick={handleSave}>
                Guardar
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <ConfirmModal
        open={Boolean(deleteTarget)}
        title="Eliminar cuenta"
        description={
          deleteTarget && (deleteTarget.turn_amount !== 0 || deleteTarget.account_amount !== 0)
            ? "Esta cuenta tiene dinero. Solo admin puede eliminar luego de confirmacion."
            : "¿Confirmas la eliminacion de la cuenta?"
        }
        confirmLabel="Eliminar"
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </section>
  );
}
