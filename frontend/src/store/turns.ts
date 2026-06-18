import { create } from "zustand";

import { api, isOffline, parseApiError } from "../lib/api";
import { useAccountStore } from "./accounts";
import { useSyncStore } from "./sync";
import { notifyError, notifyInfo } from "../ui/toast";

export type GlobalTurnSummary = {
  turn_group_id: string;
  status: "OPEN" | "CLOSED";
  opened_at: string;
  liquidity: number;
  incomes: number;
  expenses: number;
  turn_devengo: number;
  turn_cxc: number;
  turn_cxp: number;
};

type GlobalTurnSummaryApi = Omit<GlobalTurnSummary, "liquidity" | "incomes" | "expenses" | "turn_devengo" | "turn_cxc" | "turn_cxp"> & {
  liquidity: number | string;
  incomes: number | string;
  expenses: number | string;
  turn_devengo: number | string;
  turn_cxc: number | string;
  turn_cxp: number | string;
};

export type TurnStore = {
  activeGlobal?: GlobalTurnSummary;
  loading: boolean;
  openGlobalTurn: () => Promise<void>;
  closeGlobalTurn: () => Promise<void>;
  fetchActiveGlobal: (accountId?: string) => Promise<void>;
};

export const useTurnStore = create<TurnStore>((set) => ({
  activeGlobal: undefined,
  loading: false,
  openGlobalTurn: async () => {
    set({ loading: true });
    try {
      if (isOffline()) {
        await useSyncStore.getState().enqueue({
          type: "open_turn_global",
          payload: {},
        });
        notifyInfo("Turno global en cola para sincronizar");
        return;
      }
      const response = await api.post<GlobalTurnSummaryApi>("/turns/open-global");
      set({
        activeGlobal: {
          ...response.data,
          liquidity: Number(response.data.liquidity),
          incomes: Number(response.data.incomes),
          expenses: Number(response.data.expenses),
          turn_devengo: Number(response.data.turn_devengo),
          turn_cxc: Number(response.data.turn_cxc),
          turn_cxp: Number(response.data.turn_cxp),
        },
      });
      await useAccountStore.getState().fetchAccounts();
      notifyInfo("Turno global abierto");
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      set({ loading: false });
    }
  },
  closeGlobalTurn: async () => {
    set({ loading: true });
    try {
      if (isOffline()) {
        await useSyncStore.getState().enqueue({
          type: "close_turn_global",
          payload: {},
        });
        notifyInfo("Cierre global en cola para sincronizar");
        return;
      }
      const response = await api.patch<GlobalTurnSummaryApi>("/turns/close-global");
      set({
        activeGlobal: {
          ...response.data,
          liquidity: Number(response.data.liquidity),
          incomes: Number(response.data.incomes),
          expenses: Number(response.data.expenses),
          turn_devengo: Number(response.data.turn_devengo),
          turn_cxc: Number(response.data.turn_cxc),
          turn_cxp: Number(response.data.turn_cxp),
        },
      });
      await useAccountStore.getState().fetchAccounts();
      notifyInfo("Turno global cerrado");
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      set({ loading: false });
    }
  },
  fetchActiveGlobal: async (accountId) => {
    set({ loading: true });
    try {
      const response = await api.get<GlobalTurnSummaryApi>("/turns/active-global", {
        params: accountId ? { account_id: accountId } : undefined,
      });
       set({
         activeGlobal: {
           ...response.data,
           liquidity: Number(response.data.liquidity),
           incomes: Number(response.data.incomes),
           expenses: Number(response.data.expenses),
           turn_devengo: Number(response.data.turn_devengo),
           turn_cxc: Number(response.data.turn_cxc),
           turn_cxp: Number(response.data.turn_cxp),
         },
       });
    } catch {
      set({ activeGlobal: undefined });
    } finally {
      set({ loading: false });
    }
  },
}));
