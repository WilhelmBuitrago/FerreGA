import { useState, useEffect } from "react";

import { useAccountStore } from "../store/accounts";
import { useCreditStore } from "../store/credits";
import { notifyError } from "../ui/toast";
import { DatePicker } from "./DatePicker";

type CreditModalProps = {
  open: boolean;
  onClose: () => void;
  initialType?: "CREDIT_SALE" | "CREDIT_PURCHASE";
};

export function CreditModal({ open, onClose, initialType }: CreditModalProps) {
  const accounts = useAccountStore((state) => state.accounts);
  const { credits, fetchCredits, createCredit, payCredit } = useCreditStore();

  const [type, setType] = useState<"CREDIT_SALE" | "CREDIT_PURCHASE">(initialType ?? "CREDIT_SALE");
  // Create fields
  const [totalAmount, setTotalAmount] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [description, setDescription] = useState("");
  // Pay fields
  const [selectedCreditId, setSelectedCreditId] = useState<string | null>(null);
  const [paymentAccountId, setPaymentAccountId] = useState("");
  const [paymentAmount, setPaymentAmount] = useState("");
  const [paymentDescription, setPaymentDescription] = useState("");

  // Reset when modal opens
  useEffect(() => {
    if (open) {
      setType(initialType ?? "CREDIT_SALE");
      setTotalAmount("");
      setDueDate("");
      setDescription("");
      setSelectedCreditId(null);
      setPaymentAccountId("");
      setPaymentAmount("");
      setPaymentDescription("");
    }
  }, [open, initialType]);

  const pendingCredits = credits.filter(
    (c) => c.type === type && c.status !== "PAGADO"
  );

  const selectedCredit = pendingCredits.find((c) => c.id === selectedCreditId);

  const handleCreate = async () => {
    if (!totalAmount || !dueDate) return;
    const result = await createCredit({
      type,
      total_amount: Number(totalAmount),
      due_date: new Date(dueDate).toISOString(), // convert YYYY-MM-DD to ISO string
      description: description || undefined,
    });
    if (result) {
      onClose();
    }
  };

  const handlePay = async () => {
    if (!selectedCreditId || !paymentAccountId || !paymentAmount) return;
    const result = await payCredit(
      selectedCreditId,
      paymentAccountId,
      Number(paymentAmount),
      paymentDescription || undefined
    );
    if (result) {
      onClose();
    }
  };

  if (!open) return null;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 600 }}>
        <h3>Gestión de Créditos</h3>

        {/* Crear Crédito */}
        <div style={{ marginBottom: 24 }}>
          <h4>Crear Nuevo Crédito</h4>
          <div className="form-grid">
            <label>
              Tipo
              <select
                value={type}
                onChange={(e) => setType(e.target.value as "CREDIT_SALE" | "CREDIT_PURCHASE")}
              >
                <option value="CREDIT_SALE">Cuenta por Cobrar (Venta a crédito)</option>
                <option value="CREDIT_PURCHASE">Cuenta por Pagar (Compra a crédito)</option>
              </select>
            </label>

            <label>
              Monto total
              <input
                type="number"
                min="0"
                step="0.01"
                value={totalAmount}
                onChange={(e) => setTotalAmount(e.target.value)}
              />
            </label>

            <label>
              Fecha vencimiento
              <DatePicker
                value={dueDate}
                onChange={setDueDate}
                min={new Date().toISOString().split('T')[0]}
              />
            </label>

            <label>
              Descripción
              <input value={description} onChange={(e) => setDescription(e.target.value)} />
            </label>
          </div>

          <div className="modal-actions">
            <button className="button button-primary" type="button" onClick={handleCreate}>
              Crear Crédito
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
