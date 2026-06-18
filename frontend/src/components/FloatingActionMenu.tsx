import { useMemo, useState, useEffect } from "react";

import { useAccountStore } from "../store/accounts";
import { useMovementStore } from "../store/movements";
import { useTurnStore } from "../store/turns";
import { useCategoriesStore, type CategoryGroup } from "../store/categories";
import { CreditModal } from "./CreditModal";
import { AIChatModal } from "./AIChatModal";

const EMPTY = "";

type FloatingActionMenuProps = {
  activeTurnStatus: "OPEN" | "CLOSED";
};

type ModalType = "income" | "expense" | "transfer" | "close" | "credit" | null;

export function FloatingActionMenu({ activeTurnStatus }: FloatingActionMenuProps) {
  const accounts = useAccountStore((state) => state.accounts);
  const openTurn = useTurnStore((state) => state.openGlobalTurn);
  const closeTurn = useTurnStore((state) => state.closeGlobalTurn);
  const addIncome = useMovementStore((state) => state.addIncome);
  const addExpense = useMovementStore((state) => state.addExpense);
  const addTransfer = useMovementStore((state) => state.addTransfer);
  const fetchCategories = useCategoriesStore((state) => state.fetchCategories);
  const getGroupedByTipo = useCategoriesStore((state) => state.getGroupedByTipo);
  const [open, setOpen] = useState(false);
  const [modal, setModal] = useState<ModalType>(null);
  const [amount, setAmount] = useState(EMPTY);
  const [description, setDescription] = useState(EMPTY);
  const [selectedAccount, setSelectedAccount] = useState(EMPTY);
  const [sourceAccount, setSourceAccount] = useState(EMPTY);
  const [targetAccount, setTargetAccount] = useState(EMPTY);
  const [selectedCategory, setSelectedCategory] = useState(EMPTY);
  const [creditModalOpen, setCreditModalOpen] = useState(false);
  const [aiChatModalOpen, setAIChatModalOpen] = useState(false);
  const [initialCreditType, setInitialCreditType] = useState<"CREDIT_SALE" | "CREDIT_PURCHASE">("CREDIT_SALE");

  const selected = useMemo(
    () => accounts.find((account) => account.id === selectedAccount),
    [accounts, selectedAccount]
  );

  // Categorías agrupadas según el modal
  const groupedCategories = useMemo<CategoryGroup[]>(() => {
    if (modal === "income") return getGroupedByTipo("INGRESO");
    if (modal === "expense") return getGroupedByTipo("GASTO");
    return [];
  }, [modal, getGroupedByTipo]);

  useEffect(() => {
    void fetchCategories();
  }, [fetchCategories]);

  useEffect(() => {
    // Reset categoria cuando cambia el modal
    setSelectedCategory(EMPTY);
  }, [modal]);

  const resetForm = () => {
    setModal(null);
    setAmount(EMPTY);
    setDescription(EMPTY);
    setSelectedAccount(EMPTY);
    setSourceAccount(EMPTY);
    setTargetAccount(EMPTY);
    setSelectedCategory(EMPTY);
  };

  const handleSubmit = async () => {
    const amountValue = Number(amount);
    if (Number.isNaN(amountValue) || amountValue <= 0) return;

    if (modal === "income") {
      if (!selected || !selectedCategory) return;
      await addIncome({ account_id: selected.id, amount: amountValue, description: description || undefined, categoria_codigo: selectedCategory });
    }
    if (modal === "expense") {
      if (!selected || !selectedCategory) return;
      await addExpense({ account_id: selected.id, amount: amountValue, description: description || undefined, categoria_codigo: selectedCategory });
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
    resetForm();
  };

  const handleCloseTurn = async () => {
    await closeTurn();
    resetForm();
  };

  if (!accounts.length) return null;

  return (
    <div className="fab-container">
      {open ? (
        <div className="fab-menu">
          {activeTurnStatus !== "OPEN" ? (
            <button className="button button-primary" type="button" onClick={() => void openTurn()}>
              Abrir turno
            </button>
          ) : (
            <>
              <button
                className="button button-primary"
                type="button"
                onClick={() => {
                  if (!selectedAccount && accounts.length) {
                    setSelectedAccount(accounts[0].id);
                  }
                  setModal("income");
                }}
              >
                Registrar ingreso
              </button>
              <button
                className="button button-primary"
                type="button"
                onClick={() => {
                  if (!selectedAccount && accounts.length) {
                    setSelectedAccount(accounts[0].id);
                  }
                  setModal("expense");
                }}
              >
                Registrar egreso
              </button>
               <button
                 className="button button-secondary"
                 type="button"
                 onClick={() => {
                   if (!sourceAccount && accounts.length) {
                     setSourceAccount(accounts[0].id);
                   }
                   setModal("transfer");
                 }}
               >
                 Registrar transferencia
               </button>
                {/* Solo registrar crédito (CxC); los pagos/abonos se hacen en calendario */}
                <button
                  className="button button-secondary"
                  type="button"
                  onClick={() => {
                    setInitialCreditType("CREDIT_SALE");
                    setCreditModalOpen(true);
                  }}
                >
                  Crear Nuevo Crédito
                </button>
               <button className="button button-ghost" type="button" onClick={() => setModal("close")}>
                 Cerrar turno
               </button>
            </>
          )}
        </div>
      ) : null}
      <button className="fab" type="button" onClick={() => setOpen((value) => !value)}>
        +
      </button>

      {/* Star button for AI chat - positioned next to FAB */}
      <button
        className="fab fab-ai"
        type="button"
        onClick={() => setAIChatModalOpen(true)}
        title="Registrar con IA"
        aria-label="Abrir registro de ingreso con IA"
      >
        ✨
      </button>

      {modal ? (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            {modal === "close" ? (
              <>
                <h3>Cerrar turno</h3>
                <p>¿Confirmas el cierre del turno actual?</p>
                <div className="modal-actions">
                  <button className="button button-ghost" type="button" onClick={resetForm}>
                    Cancelar
                  </button>
                  <button className="button button-primary" type="button" onClick={handleCloseTurn}>
                    Confirmar
                  </button>
                </div>
              </>
            ) : (
               <>
                 <h3>
                   {modal === "transfer" ? "Transferencia" : modal === "income" ? "Ingreso" : "Egreso"}
                 </h3>
                 <div className="form-grid">
                   {modal === "income" || modal === "expense" ? (
                     <>
                       <label>
                         Cuenta
                         <select value={selectedAccount} onChange={(event) => setSelectedAccount(event.target.value)}>
                           <option value="">Selecciona una cuenta</option>
                           {accounts.map((account) => (
                             <option key={account.id} value={account.id}>
                               {account.name}
                             </option>
                           ))}
                         </select>
                       </label>
                       <label>
                         Categoría
                         <select value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value)}>
                           <option value="">Selecciona una categoría</option>
                           {groupedCategories.map((group) => (
                             <optgroup key={group.grupo} label={group.grupo}>
                               {group.categories.map((cat) => (
                                 <option key={cat.codigo} value={cat.codigo}>
                                   {cat.nombre}
                                 </option>
                               ))}
                             </optgroup>
                           ))}
                         </select>
                       </label>
                      </>
                   ) : null}
                   {modal === "transfer" ? (
                     <>
                       <label>
                         Cuenta origen
                         <select value={sourceAccount} onChange={(event) => setSourceAccount(event.target.value)}>
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
                       <select value={targetAccount} onChange={(event) => setTargetAccount(event.target.value)}>
                         <option value="">Selecciona una cuenta</option>
                         {accounts
                           .filter((account) => account.id !== sourceAccount)
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
                   <button className="button button-ghost" type="button" onClick={resetForm}>
                     Cancelar
                   </button>
                   <button className="button button-primary" type="button" onClick={handleSubmit}>
                     Confirmar
                   </button>
                 </div>
               </>
             )}
           </div>
         </div>
       ) : null}

      <CreditModal open={creditModalOpen} onClose={() => setCreditModalOpen(false)} initialType={initialCreditType} />
      <AIChatModal open={aiChatModalOpen} onClose={() => setAIChatModalOpen(false)} />
    </div>
  );
}