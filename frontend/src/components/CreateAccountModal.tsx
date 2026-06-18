import { useEffect, useState } from "react";

import { useAccountStore } from "../store/accounts";

type CreateAccountModalProps = {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
};

export function CreateAccountModal({ open, onClose, onSuccess }: CreateAccountModalProps) {
  const createAccount = useAccountStore((state) => state.createAccount);
  const loading = useAccountStore((state) => state.loading);
  const [name, setName] = useState("");
  const [initialBalance, setInitialBalance] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setName("");
      setInitialBalance("");
      setError(null);
    }
  }, [open]);

  if (!open) return null;

  const handleCreate = async () => {
    const trimmed = name.trim();
    if (!trimmed) {
      setError("Ingresa un nombre valido");
      return;
    }
    const balance = initialBalance ? Number(initialBalance) : undefined;
    const ok = await createAccount(trimmed, balance);
    if (ok) {
      onSuccess?.();
      onClose();
    }
  };

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <h3>Nueva cuenta</h3>
        <p className="page-subtitle">Completa el nombre y confirma la creacion.</p>
        <label>
          Nombre
          <input
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              if (error) setError(null);
            }}
          />
        </label>
        <label>
          Saldo inicial (opcional)
          <input
            type="number"
            min="0"
            step="0.01"
            value={initialBalance}
            onChange={(event) => setInitialBalance(event.target.value)}
          />
        </label>
        {error ? <p className="page-subtitle">{error}</p> : null}
        <div className="modal-actions">
          <button className="button button-ghost" type="button" onClick={onClose} disabled={loading}>
            Cancelar
          </button>
          <button className="button button-primary" type="button" onClick={handleCreate} disabled={loading}>
            Crear
          </button>
        </div>
      </div>
    </div>
  );
}
