import { create } from "zustand";

import { api, parseApiError } from "../lib/api";
import { useTurnStore } from "./turns";
import { useMovementStore } from "./movements";
import { notifyError, notifyInfo } from "../ui/toast";

export type Credit = {
  id: string;
  account_id: string | null;
  type: "CREDIT_SALE" | "CREDIT_PURCHASE";
  total_amount: number;
  paid_amount: number;
  due_date: string;
  status: "PENDIENTE" | "PARCIAL" | "PAGADO";
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type CreditStore = {
  credits: Credit[];
  loading: boolean;
  fetchCredits: (accountId?: string, status?: string) => Promise<void>;
  createCredit: (payload: {
    type: "CREDIT_SALE" | "CREDIT_PURCHASE";
    total_amount: number;
    due_date: string;
    description?: string;
  }) => Promise<Credit | null>;
  payCredit: (creditId: string, accountId: string, amount: number, description?: string) => Promise<Credit | null>;
  updateCredit: (creditId: string, updates: {
    total_amount?: number;
    due_date?: string;
    description?: string;
  }) => Promise<Credit | null>;
};

export const useCreditStore = create<CreditStore>((set) => ({
  credits: [],
  loading: false,
  fetchCredits: async (accountId, status) => {
    set({ loading: true });
    try {
      const params: any = {};
      if (accountId) params.account_id = accountId;
      if (status) params.status = status;
      const response = await api.get("/credits", { params });
      let items: any[] = [];
      if (Array.isArray(response.data)) {
        items = response.data;
      } else if (response.data?.items) {
        items = response.data.items;
      } else {
        console.warn("Formato inesperado en /credits:", response.data);
        items = [];
      }
      const normalized = items.map((c) => ({
        ...c,
        total_amount: Number(c.total_amount ?? 0),
        paid_amount: Number(c.paid_amount ?? 0),
      }));
      set({ credits: normalized });
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      set({ loading: false });
    }
  },
   createCredit: async (payload) => {
     set({ loading: true });
     try {
       const response = await api.post<any>("/credits", {
         ...payload,
         due_date: new Date(payload.due_date).toISOString(),
       });
       const credit: Credit = {
         ...response.data,
         total_amount: Number(response.data.total_amount),
         paid_amount: Number(response.data.paid_amount),
       };
       notifyInfo("Crédito registrado");
       await useCreditStore.getState().fetchCredits();
       await useTurnStore.getState().fetchActiveGlobal();
       useMovementStore.getState().touch(); // refrescar resumen
       return credit;
     } catch (error) {
       notifyError(parseApiError(error));
       return null;
     } finally {
       set({ loading: false });
     }
   },
   payCredit: async (creditId, accountId, amount, description) => {
     set({ loading: true });
     try {
       const response = await api.post<any>(`/credits/${creditId}/pay`, {
         amount,
         account_id: accountId,
         description,
       });
       const credit: Credit = {
         ...response.data,
         total_amount: Number(response.data.total_amount),
         paid_amount: Number(response.data.paid_amount),
       };
       notifyInfo("Pago registrado");
       await useCreditStore.getState().fetchCredits();
       await useTurnStore.getState().fetchActiveGlobal();
       useMovementStore.getState().touch(); // refrescar resumen
       return credit;
     } catch (error) {
       notifyError(parseApiError(error));
       return null;
     } finally {
       set({ loading: false });
     }
   },
   updateCredit: async (creditId, updates) => {
     set({ loading: true });
     try {
       const response = await api.patch<any>(`/credits/${creditId}`, updates);
       const credit: Credit = {
         ...response.data,
         total_amount: Number(response.data.total_amount),
         paid_amount: Number(response.data.paid_amount),
       };
       notifyInfo("Crédito actualizado");
       await useCreditStore.getState().fetchCredits();
       await useTurnStore.getState().fetchActiveGlobal();
       useMovementStore.getState().touch(); // refrescar resumen
       return credit;
     } catch (error) {
       notifyError(parseApiError(error));
       return null;
     } finally {
       set({ loading: false });
     }
   },
}));
