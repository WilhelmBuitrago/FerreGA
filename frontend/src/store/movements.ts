import { create } from "zustand";

import { api, isOffline, parseApiError } from "../lib/api";
import { useAccountStore } from "./accounts";
import { useTurnStore } from "./turns";
import { useSyncStore } from "./sync";
import { notifyError, notifyInfo } from "../ui/toast";

export type MovementStore = {
  loading: boolean;
  lastUpdate: number;
  addIncome: (payload: { account_id: string; amount: number; description?: string; categoria_codigo: string }) => Promise<void>;
  addExpense: (payload: { account_id: string; amount: number; description?: string; categoria_codigo: string }) => Promise<void>;
  addTransfer: (payload: {
    source_account_id: string;
    target_account_id: string;
    amount: number;
    description?: string;
  }) => Promise<void>;
  touch: () => void;
};

export const useMovementStore = create<MovementStore>((set, get) => ({
  loading: false,
  lastUpdate: 0,
  addIncome: async (payload) => {
    set({ loading: true });
    try {
      const idempotency_key = "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}`;
      if (isOffline()) {
        await useSyncStore.getState().enqueue({
          type: "income",
          payload: { ...payload, idempotency_key },
        });
        notifyInfo("Ingreso en cola para sincronizar");
        set({ lastUpdate: Date.now() });
        return;
      }
      await api.post("/movements/income", { ...payload, idempotency_key });
      await useAccountStore.getState().fetchAccounts();
      await useAccountStore.getState().fetchAccountDetail(payload.account_id);
      await useTurnStore.getState().fetchActiveGlobal();
      set({ lastUpdate: Date.now() });
      notifyInfo("Ingreso registrado");
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      set({ loading: false });
    }
  },
  addExpense: async (payload) => {
    set({ loading: true });
    try {
      const idempotency_key = "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}`;
      if (isOffline()) {
        await useSyncStore.getState().enqueue({
          type: "expense",
          payload: { ...payload, idempotency_key },
        });
        notifyInfo("Egreso en cola para sincronizar");
        set({ lastUpdate: Date.now() });
        return;
      }
      await api.post("/movements/expense", { ...payload, idempotency_key });
      await useAccountStore.getState().fetchAccounts();
      await useAccountStore.getState().fetchAccountDetail(payload.account_id);
      await useTurnStore.getState().fetchActiveGlobal();
      set({ lastUpdate: Date.now() });
      notifyInfo("Egreso registrado");
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      set({ loading: false });
    }
  },
  addTransfer: async (payload) => {
    set({ loading: true });
    try {
      const idempotency_key = "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}`;
      if (isOffline()) {
        await useSyncStore.getState().enqueue({
          type: "transfer",
          payload: { ...payload, idempotency_key },
        });
        notifyInfo("Transferencia en cola para sincronizar");
        set({ lastUpdate: Date.now() });
        return;
      }
      await api.post("/movements/transfer", { ...payload, idempotency_key });
      await useAccountStore.getState().fetchAccounts();
      await useAccountStore.getState().fetchAccountDetail(payload.source_account_id);
      await useAccountStore.getState().fetchAccountDetail(payload.target_account_id);
      await useTurnStore.getState().fetchActiveGlobal();
      set({ lastUpdate: Date.now() });
      notifyInfo("Transferencia registrada");
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      set({ loading: false });
    }
  },
  touch: () => {
    set({ lastUpdate: Date.now() });
  },
}));
