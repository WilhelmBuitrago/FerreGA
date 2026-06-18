import { useEffect, useMemo, useState } from "react";

import { ConfirmModal } from "../components/ConfirmModal";
import { api, parseApiError } from "../lib/api";
import { useAccountStore } from "../store/accounts";
import { useCategoriesStore } from "../store/categories";
import { notifyError, notifyInfo } from "../ui/toast";

type MovementRow = {
  id: string;
  type: string;
  amount: number;
  description?: string | null;
  categoria_codigo?: string | null;
  timestamp: string;
  turn_id: string;
};

export function AdminTransactions() {
  const accounts = useAccountStore((state) => state.accounts);
  const account = useAccountStore((state) => state.selected);
  const fetchAccounts = useAccountStore((state) => state.fetchAccounts);
  const fetchAccountDetail = useAccountStore((state) => state.fetchAccountDetail);
  const getCategoryName = useCategoriesStore((state) => state.getNombreByCodigo);
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [editing, setEditing] = useState<MovementRow | null>(null);
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<MovementRow | null>(null);

  useEffect(() => {
    void fetchAccounts(true);
  }, [fetchAccounts]);

  useEffect(() => {
    if (!selectedAccountId && accounts.length) {
      setSelectedAccountId(accounts[0].id);
    }
  }, [accounts, selectedAccountId]);

  useEffect(() => {
    if (selectedAccountId) {
      void fetchAccountDetail(selectedAccountId);
    }
  }, [selectedAccountId, fetchAccountDetail]);

  const movements = useMemo<MovementRow[]>(() => {
    if (!account) return [];
    return account.history.flatMap((turn) =>
      turn.movements.map((movement) => ({
        ...movement,
        turn_id: turn.id,
      }))
    );
  }, [account]);

  // Mapeo de tipo a etiqueta amigable
  const getTipoLabel = (type: string) => {
    switch (type) {
      case "INCOME":
        return "Ingreso";
      case "EXPENSE":
        return "Egreso";
      case "TRANSFER":
        return "Transferencia";
      default:
        return type;
    }
  };

  // Formatear fecha a dd/mm/aaaa
  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("es-ES");
  };

  const openEdit = (movement: MovementRow) => {
    setEditing(movement);
    setAmount(movement.amount.toFixed(2));
    setDescription(movement.description ?? "");
  };

  const closeEdit = () => {
    setEditing(null);
    setAmount("");
    setDescription("");
  };

  const handleSave = async () => {
    if (!editing) return;
    const amountValue = amount.trim() ? Number(amount) : null;
    if (amountValue !== null && Number.isNaN(amountValue)) return;
    try {
      await api.patch(`/movements/${editing.id}`, {
        amount: amountValue,
        description: description.trim() || null,
      });
      notifyInfo("Transaccion actualizada");
      if (selectedAccountId) {
        await fetchAccountDetail(selectedAccountId);
      }
      closeEdit();
    } catch (error) {
      notifyError(parseApiError(error));
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await api.delete(`/movements/${deleteTarget.id}`);
      notifyInfo("Transaccion eliminada");
      if (selectedAccountId) {
        await fetchAccountDetail(selectedAccountId);
      }
      setDeleteTarget(null);
    } catch (error) {
      notifyError(parseApiError(error));
    }
  };

  return (
    <section className="card">
      <div className="page-header">
        <div>
          <h3>Transacciones</h3>
          <p className="page-subtitle">Edita ingresos y egresos. Transferencias solo lectura.</p>
        </div>
      </div>
      <label>
        Cuenta
        <select value={selectedAccountId} onChange={(event) => setSelectedAccountId(event.target.value)}>
          {accounts.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <table className="table">
        <thead>
          <tr>
            <th>Tipo de Registro</th>
            <th>Categoría</th>
            <th>Descripcion</th>
            <th>Monto</th>
            <th>Fecha</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          {movements.map((movement) => (
            <tr key={movement.id}>
              <td>{getTipoLabel(movement.type)}</td>
              <td>{movement.categoria_codigo ? getCategoryName(movement.categoria_codigo) : "-"}</td>
              <td>{movement.description ?? "-"}</td>
              <td>{movement.amount.toFixed(2)}</td>
              <td>{formatDate(movement.timestamp)}</td>
              <td>
                <div className="modal-actions">
                  <button
                    className="button button-ghost"
                    type="button"
                    onClick={() => openEdit(movement)}
                    disabled={movement.type === "TRANSFER"}
                  >
                    Editar
                  </button>
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => setDeleteTarget(movement)}
                    disabled={movement.type === "TRANSFER"}
                  >
                    Eliminar
                  </button>
                </div>
              </td>
            </tr>
          ))}
          {!movements.length ? (
            <tr>
              <td colSpan={6}>No hay transacciones registradas.</td>
            </tr>
          ) : null}
        </tbody>
      </table>

      {editing ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <h3>Editar transaccion</h3>
            <div className="form-grid">
              <label>
                Monto
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                />
              </label>
              <label>
                Descripcion
                <input value={description} onChange={(event) => setDescription(event.target.value)} />
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
        title="Eliminar transaccion"
        description="¿Confirmas la eliminacion de la transaccion?"
        confirmLabel="Eliminar"
        onCancel={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
      />
    </section>
  );
}
