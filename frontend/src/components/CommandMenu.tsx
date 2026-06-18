import { useMemo, useState } from "react";

import { useAccountStore } from "../store/accounts";
import { useMovementStore } from "../store/movements";

const EMPTY = "";

type CommandMenuProps = {
  accountId: string;
};

type ModalType = "income" | "expense" | "transfer" | null;

export function CommandMenu({ accountId }: CommandMenuProps) {
  const accounts = useAccountStore((state) => state.accounts);
  const addIncome = useMovementStore((state) => state.addIncome);
  const addExpense = useMovementStore((state) => state.addExpense);
  const addTransfer = useMovementStore((state) => state.addTransfer);
  const [modal, setModal] = useState<ModalType>(null);
  const [amount, setAmount] = useState(EMPTY);
  const [description, setDescription] = useState(EMPTY);
  const [sourceAccount, setSourceAccount] = useState(EMPTY);
  const [targetAccount, setTargetAccount] = useState(EMPTY);

  const currentAccount = useMemo(
    () => accounts.find((account) => account.id === accountId),
    [accounts, accountId]
  );

  const close = () => {
    setModal(null);
    setAmount(EMPTY);
    setDescription(EMPTY);
    setSourceAccount(EMPTY);
    setTargetAccount(EMPTY);
  };

  const handleSubmit = async () => {
    const amountValue = Number(amount);
    if (!currentAccount || Number.isNaN(amountValue) || amountValue <= 0) return;

    if (modal === "income") {
      await addIncome({ account_id: accountId, amount: amountValue, description: description || undefined });
    }
    if (modal === "expense") {
      await addExpense({ account_id: accountId, amount: amountValue, description: description || undefined });
    }
    if (modal === "transfer") {
      if (!sourceAccount || !targetAccount) return;
      await addTransfer({
        source_account_id: sourceAccount,
        target_account_id: targetAccount,
        amount: amountValue,
        description: description || undefined,
      });
    }
    close();
  };

  return (
    <div className="command-menu">
      <button className="button button-primary" type="button" onClick={() => setModal("income")}>
        Agregar ingreso
      </button>
      <button className="button button-primary" type="button" onClick={() => setModal("expense")}>
        Agregar egreso
      </button>
      <button
        className="button button-secondary"
        type="button"
        onClick={() => {
          setSourceAccount(accountId);
          setModal("transfer");
        }}
      >
        Transferir
      </button>

      {modal && (
        <div className="dropdown-menu" role="dialog" aria-modal="true">
          <h3>
            {modal === "transfer"
              ? "Transferencia"
              : modal === "income"
              ? "Ingreso"
              : "Egreso"}
          </h3>
          <div className="form-grid">
            {modal === "transfer" ? (
              <>
                <label>
                  Cuenta origen
                  <select
                    value={sourceAccount || accountId}
                    onChange={(event) => setSourceAccount(event.target.value)}
                  >
                    <option value="">Selecciona una cuenta</option>
                    {accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Cuenta destino
                  <select
                    value={targetAccount}
                    onChange={(event) => setTargetAccount(event.target.value)}
                  >
                    <option value="">Selecciona una cuenta</option>
                    {accounts
                      .filter((account) => account.id !== (sourceAccount || accountId))
                      .map((account) => (
                        <option key={account.id} value={account.id}>
                          {account.name}
                        </option>
                      ))}
                  </select>
                </label>
              </>
            ) : null}
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
            <button className="button button-ghost" type="button" onClick={close}>
              Cancelar
            </button>
            <button className="button button-primary" type="button" onClick={handleSubmit}>
              Confirmar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
