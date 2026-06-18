import { useEffect, useState, useMemo } from "react";

import { useCreditStore } from "../store/credits";
import { useAccountStore } from "../store/accounts";
import { notifyError, notifyInfo } from "../ui/toast";
import { DatePicker } from "../components/DatePicker";

export function CalendarPage() {
  const { credits = [], fetchCredits, loading: creditsLoading, updateCredit, payCredit } = useCreditStore();
  const { accounts = [], fetchAccounts } = useAccountStore();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [editCredit, setEditCredit] = useState<any>(null);
  const [payCreditState, setPayCreditState] = useState<any>(null);
  const [payMode, setPayMode] = useState<"full" | "partial">("full");
  const [editForm, setEditForm] = useState({
    total_amount: "",
    due_date: "",
    description: "",
  });
  const [payForm, setPayForm] = useState({
    account_id: "",
    amount: "",
    description: "",
  });
  const [payConfirmDiff, setPayConfirmDiff] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cargar créditos y cuentas
  useEffect(() => {
    void fetchCredits();
    void fetchAccounts();
  }, [fetchCredits, fetchAccounts]);

  // Limpiar modales al cambiar fecha seleccionada
  useEffect(() => {
    if (!selectedDate) {
      setEditCredit(null);
      setPayCreditState(null);
    }
  }, [selectedDate]);

  // Calcular grid del mes
  const monthGrid = useMemo(() => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startDayOfWeek = firstDay.getDay(); // 0 (domingo) - 6 (sábado)
    const grid: (Date | null)[] = [];
    for (let i = 0; i < startDayOfWeek; i++) grid.push(null);
    for (let d = 1; d <= daysInMonth; d++) grid.push(new Date(year, month, d));
    return grid;
  }, [currentDate]);

  // Mapa de créditos por día (tratando fecha como local, sin zona)
  const dayCreditsMap = useMemo(() => {
    const map = new Map<string, { cxc: number; cxp: number; credits: any[] }>();
    credits.forEach((c) => {
      try {
        // Extraer solo la parte de fecha (YYYY-MM-DD) y crear fecha local
        const datePart = c.due_date.split('T')[0];
        const [year, month, day] = datePart.split('-').map(Number);
        // Crear fecha local (mes 0-indexado)
        const due = new Date(year, month - 1, day);
        const key = due.toDateString();
        const entry = map.get(key) || { cxc: 0, cxp: 0, credits: [] };
        if (c.type === "CREDIT_SALE") entry.cxc++;
        else if (c.type === "CREDIT_PURCHASE") entry.cxp++;
        entry.credits.push(c);
        map.set(key, entry);
      } catch (e) {
        console.warn("Invalid due_date:", c.due_date);
      }
    });
    return map;
  }, [credits]);

  // Créditos para la fecha seleccionada
  const selectedCredits = useMemo(() => {
    if (!selectedDate) return [];
    const dateKey = selectedDate.toDateString();
    const entry = dayCreditsMap.get(dateKey);
    return entry ? entry.credits : [];
  }, [selectedDate, dayCreditsMap]);

  // Navegación de mes
  const changeMonth = (offset: number) => {
    setCurrentDate((prev) => {
      const d = new Date(prev);
      d.setMonth(d.getMonth() + offset);
      return d;
    });
  };

  // Abrir modal de edición
  const openEdit = (credit: any) => {
    setEditCredit(credit);
    const isoDate = credit.due_date.split("T")[0];
    setEditForm({
      total_amount: credit.total_amount.toString(),
      due_date: isoDate,
      description: credit.description || "",
    });
    setPayCreditState(null);
    setError(null);
  };

  // Abrir modal de pago (modo: 'full' | 'partial')
  const openPay = (credit: any, mode: "full" | "partial") => {
    setPayCreditState(credit);
    setPayMode(mode);
    const remaining = (credit.total_amount - credit.paid_amount).toFixed(2);
    setPayForm({
      account_id: "",
      amount: mode === "partial" ? remaining : "",
      description: credit.type === "CREDIT_SALE" ? "Cobro de crédito" : "Pago de deuda",
    });
    setPayConfirmDiff(false);
    setEditCredit(null);
    setError(null);
  };

  // Submit edición
  const handleEditSubmit = async () => {
    if (!editCredit) return;
    const updates: any = {};
    const newTotal = Number(editForm.total_amount);
    if (!isNaN(newTotal) && newTotal > 0) updates.total_amount = newTotal;
    if (editForm.due_date) updates.due_date = new Date(editForm.due_date).toISOString();
    if (editForm.description !== undefined) updates.description = editForm.description;
    const ok = await updateCredit(editCredit.id, updates);
    if (ok) {
      setEditCredit(null);
      notifyInfo("Crédito actualizado");
    } else {
      setError("No se pudo actualizar");
    }
  };

  // Submit pago/abono
  const handlePaySubmit = async () => {
    if (!payCreditState) return;
    const account_id = payForm.account_id;
    const remaining = payCreditState.total_amount - payCreditState.paid_amount;
    let amount: number;
    if (payMode === "full") {
      amount = Number(remaining.toFixed(2));
    } else {
      amount = Number(payForm.amount);
      if (isNaN(amount) || amount <= 0) {
        setError("Monto inválido");
        return;
      }
      if (amount >= remaining - 0.001) {
        setError("El monto del abono debe ser menor al total restante. Use 'Cobrar/Pagar' para pagar completo.");
        return;
      }
      // Confirmación requerida siempre en abono (puesto que es diferente)
      if (!payConfirmDiff) {
        setError("Debe confirmar el abono (marque la casilla).");
        return;
      }
    }
    if (!account_id) {
      setError("Seleccione una cuenta");
      return;
    }
    const ok = await payCredit(payCreditState.id, account_id, amount, payForm.description);
    if (ok) {
      setPayCreditState(null);
      setPayConfirmDiff(false);
      notifyInfo(payMode === "full" ? "Pago registrado" : "Abono registrado");
    } else {
      setError("Error registrando pago");
    }
  };

  const monthLabel = currentDate.toLocaleDateString("es-ES", { month: "long", year: "numeric" });

  return (
    <section className="card">
      <div className="page-header">
        <div>
          <h2 className="page-title">Calendario de Créditos</h2>
          <p className="page-subtitle">{monthLabel}</p>
        </div>
        <div>
          <button className="button button-ghost" onClick={() => changeMonth(-1)}>‹</button>
          <button className="button button-ghost" onClick={() => setCurrentDate(new Date())}>Hoy</button>
          <button className="button button-ghost" onClick={() => changeMonth(1)}>›</button>
        </div>
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {/* Días de la semana */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4, marginBottom: 8 }}>
        {["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"].map((day) => (
          <div key={day} style={{ textAlign: "center", fontWeight: "bold", fontSize: 12 }}>{day}</div>
        ))}
      </div>

      {/* Grid de días */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4 }}>
        {monthGrid.map((date, idx) => {
          if (!date) return <div key={idx} style={{ minHeight: 48 }}></div>;
          const dateKey = date.toDateString();
          const stats = dayCreditsMap.get(dateKey) || { cxc: 0, cxp: 0, credits: [] };
          const isSelected = selectedDate && selectedDate.toDateString() === dateKey;
          const isToday = date.toDateString() === new Date().toDateString();
          return (
            <div
              key={idx}
              onClick={() => setSelectedDate(date)}
              style={{
                minHeight: 48,
                padding: 6,
                borderRadius: 8,
                border: isSelected ? "2px solid var(--accent)" : "1px solid #e2e8f0",
                background: isToday ? "#fef9c3" : "transparent",
                cursor: "pointer",
                position: "relative",
              }}
            >
              <div style={{ fontSize: 14, fontWeight: isToday ? "bold" : "normal", textAlign: "right" }}>
                {date.getDate()}
              </div>
              <div style={{ display: "flex", gap: 3, marginTop: 4, justifyContent: "center" }}>
                {stats.cxc > 0 && <span title={`${stats.cxc} cobrar`} style={{ width: 6, height: 6, borderRadius: "50%", background: "#16a34a" }} />}
                {stats.cxp > 0 && <span title={`${stats.cxp} pagar`} style={{ width: 6, height: 6, borderRadius: "50%", background: "#dc2626" }} />}
              </div>
            </div>
          );
        })}
      </div>

      {/* Panel de créditos del día seleccionado */}
      {selectedDate && (
        <div style={{ marginTop: 24 }}>
          <h3>Créditos para {selectedDate.toLocaleDateString("es-ES")}</h3>
           {creditsLoading ? (
             <p>Cargando...</p>
           ) : selectedCredits.length === 0 ? (
             <p>No hay créditos en esta fecha.</p>
           ) : (
             <ul style={{ listStyle: "none", padding: 0 }}>
               {selectedCredits.map((c) => {
                 const remaining = c.total_amount - c.paid_amount;
                 const isPaid = c.status === "PAGADO";
                 const statusLabel = isPaid
                   ? (c.type === "CREDIT_SALE" ? "Cobrado" : "Pagado")
                   : c.status === "PARCIAL"
                   ? (c.type === "CREDIT_SALE" ? "Parcialmente cobrado" : "Parcialmente pagado")
                   : (c.type === "CREDIT_SALE" ? "No cobrado" : "No pagado");
                 return (
                   <li key={c.id} className="card" style={{ marginBottom: 8 }}>
                     <div className="page-header">
                       <div>
                         <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                           <strong>{c.type === "CREDIT_SALE" ? "Venta a crédito" : "Compra a crédito"}</strong>
                           <span style={{
                             fontSize: 12,
                             padding: "2px 6px",
                             borderRadius: 4,
                             background: isPaid ? "#dcfce7" : c.status === "PARCIAL" ? "#fef9c3" : "#fee2e2",
                             color: isPaid ? "#166534" : c.status === "PARCIAL" ? "#854d0e" : "#991b1b",
                           }}>
                             {statusLabel}
                           </span>
                         </div>
                         <p className="page-subtitle">
                           {c.description ?? "Sin descripción"}<br />
                           Vence: {new Date(c.due_date).toLocaleDateString('es-ES')}<br />
                           Total: {c.total_amount.toFixed(2)} • Pagado: {c.paid_amount.toFixed(2)} • Restante: {(c.total_amount - c.paid_amount).toFixed(2)}
                         </p>
                       </div>
                       {!isPaid && remaining > 0 && (
                         <div style={{ display: "flex", gap: 8 }}>
                           <button className="button button-secondary" onClick={() => openEdit(c)}>Editar</button>
                           <button className="button button-primary" onClick={() => openPay(c, "full")}>
                             {c.type === "CREDIT_SALE" ? "Cobrar" : "Pagar"}
                           </button>
                           {remaining > 0 && (
                             <button className="button button-secondary" onClick={() => openPay(c, "partial")}>
                               Abonar
                             </button>
                           )}
                         </div>
                       )}
                     </div>
                   </li>
                 );
               })}
             </ul>
           )}
        </div>
      )}

      {/* Modal Editar Crédito */}
      {editCredit && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={() => setEditCredit(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Editar Crédito</h3>
            <div className="form-grid">
              <label>
                Monto total
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={editForm.total_amount}
                  onChange={(e) => setEditForm({ ...editForm, total_amount: e.target.value })}
                />
              </label>
               <label>
                 Fecha vencimiento
                 <DatePicker
                   value={editForm.due_date}
                   onChange={(iso) => setEditForm({ ...editForm, due_date: iso })}
                   min={new Date().toISOString().split("T")[0]}
                 />
               </label>
              <label>
                Descripción
                <input
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                />
              </label>
            </div>
            <div className="modal-actions">
              <button className="button button-ghost" onClick={() => setEditCredit(null)}>Cancelar</button>
              <button className="button button-primary" onClick={handleEditSubmit}>Guardar</button>
            </div>
          </div>
        </div>
      )}

       {/* Modal Pagar / Cobrar / Abonar */}
       {payCreditState && (
         <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={() => setPayCreditState(null)}>
           <div className="modal" onClick={(e) => e.stopPropagation()}>
             <h3>
               {payMode === "full"
                 ? (payCreditState.type === "CREDIT_SALE" ? "Cobrar crédito" : "Pagar deuda")
                 : (payCreditState.type === "CREDIT_SALE" ? "Abonar a crédito" : "Abonar a deuda")
               }
             </h3>
             <p>
               Total restante: <strong>{(payCreditState.total_amount - payCreditState.paid_amount).toFixed(2)}</strong>
             </p>
             <div className="form-grid">
               <label>
                 Cuenta (caja)
                 <select
                   value={payForm.account_id}
                   onChange={(e) => setPayForm({ ...payForm, account_id: e.target.value })}
                 >
                   <option value="">Selecciona una cuenta</option>
                   {accounts.map((a) => (
                     <option key={a.id} value={a.id}>{a.name}</option>
                   ))}
                 </select>
               </label>
               {payMode === "partial" && (
                 <label>
                   Monto a abonar
                   <input
                     type="number"
                     min="0"
                     step="0.01"
                     value={payForm.amount}
                     onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })}
                   />
                 </label>
               )}
               <label>
                 Descripción
                 <input
                   value={payForm.description}
                   onChange={(e) => setPayForm({ ...payForm, description: e.target.value })}
                 />
               </label>
             </div>
             {payMode === "partial" && (
               <div style={{ margin: "8px 0" }}>
                 <label>
                   <input
                     type="checkbox"
                     checked={payConfirmDiff}
                     onChange={(e) => setPayConfirmDiff(e.target.checked)}
                   />
                   Confirmo que el monto es intencional (diferente al total restante)
                 </label>
               </div>
             )}
             <div className="modal-actions">
               <button className="button button-ghost" onClick={() => setPayCreditState(null)}>Cancelar</button>
               <button
                 className="button button-primary"
                 onClick={handlePaySubmit}
                 disabled={payMode === "partial" ? !payForm.account_id || !payForm.amount : !payForm.account_id}
               >
                 {payMode === "full"
                   ? "Confirmar " + (payCreditState.type === "CREDIT_SALE" ? "cobro" : "pago")
                   : "Confirmar abono"
                 }
               </button>
             </div>
           </div>
         </div>
       )}
    </section>
  );
}
