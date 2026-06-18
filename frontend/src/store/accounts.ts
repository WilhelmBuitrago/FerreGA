import { create } from "zustand";

import { api, parseApiError } from "../lib/api";
import { notifyError, notifyInfo } from "../ui/toast";

export type AccountSummary = {
  id: string;
  name: string;
  turn_amount: number;
  account_amount: number;
  difference: number;
  categoria?: string;
};

type AccountSummaryApi = Omit<AccountSummary, "turn_amount" | "account_amount" | "difference"> & {
  turn_amount: number | string;
  account_amount: number | string;
  difference: number | string;
};

export type AccountDetail = {
  id: string;
  name: string;
  liquidity: number;
  incomes: number;
  expenses: number;
  history: Array<{
    id: string;
    start_amount: number;
    end_amount?: number | null;
    status: string;
    created_at: string;
    closed_at?: string | null;
    movements: Array<{
      id: string;
      type: string;
      amount: number;
      description?: string | null;
      categoria_codigo?: string | null;
      timestamp: string;
    }>;
  }>;
};

type AccountDetailApi = Omit<AccountDetail, "liquidity" | "incomes" | "expenses" | "history"> & {
  liquidity: number | string;
  incomes: number | string;
  expenses: number | string;
  history: Array<{
    id: string;
    start_amount: number | string;
    end_amount?: number | string | null;
    status: string;
    created_at: string;
    closed_at?: string | null;
    movements: Array<{
      id: string;
      type: string;
      amount: number | string;
      description?: string | null;
      categoria_codigo?: string | null;
      timestamp: string;
    }>;
  }>;
};

export type AccountStore = {
  accounts: AccountSummary[];
  selected?: AccountDetail;
  loading: boolean;
  fetchAccounts: (includeInactive?: boolean) => Promise<void>;
  fetchAccountDetail: (id: string) => Promise<void>;
  createAccount: (name: string) => Promise<boolean>;
  updateAccount: (
    id: string,
    payload: { name?: string; account_amount?: number | null },
    includeInactive?: boolean
  ) => Promise<boolean>;
  deleteAccount: (
    id: string,
    options?: { force?: boolean; hardDelete?: boolean; includeInactive?: boolean }
  ) => Promise<void>;
};

const normalizeSummary = (account: AccountSummaryApi): AccountSummary => ({
  ...account,
  turn_amount: Number(account.turn_amount),
  account_amount: Number(account.account_amount),
  difference: Number(account.difference),
  categoria: account.categoria ?? "ACTIVO",
});

const normalizeDetail = (account: AccountDetailApi): AccountDetail => ({
  id: account.id,
  name: account.name,
  liquidity: Number(account.liquidity),
  incomes: Number(account.incomes),
  expenses: Number(account.expenses),
  history: account.history.map((turn) => ({
    ...turn,
    start_amount: Number(turn.start_amount),
    end_amount: turn.end_amount === null || turn.end_amount === undefined ? null : Number(turn.end_amount),
    movements: turn.movements.map((movement) => ({
      ...movement,
      amount: Number(movement.amount),
      categoria_codigo: movement.categoria_codigo ?? null,
    })),
  })),
});

export const useAccountStore = create<AccountStore>((set) => ({
  accounts: [],
  selected: undefined,
  loading: false,
  fetchAccounts: async (includeInactive = false) => {
    set({ loading: true });
    try {
      const response = await api.get<any>("/accounts", {
        params: includeInactive ? { include_inactive: true } : undefined,
      });
      let items: any[] = [];
      if (Array.isArray(response.data)) {
        items = response.data;
      } else if (response.data?.items) {
        items = response.data.items;
      } else {
        console.warn("Formato inesperado en /accounts:", response.data);
        items = [];
      }
      set({ accounts: items.map(normalizeSummary) });
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      set({ loading: false });
    }
  },
  fetchAccountDetail: async (id) => {
    set({ loading: true });
    try {
      const response = await api.get<AccountDetailApi>(`/accounts/${id}`);
      set({ selected: normalizeDetail(response.data) });
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      set({ loading: false });
    }
  },
  createAccount: async (name, initialBalance) => {
    set({ loading: true });
    try {
      await api.post("/accounts", { name, initial_balance: initialBalance || undefined });
      notifyInfo("Cuenta creada");
      const response = await api.get<AccountSummaryApi[]>("/accounts");
      set({ accounts: response.data.map(normalizeSummary) });
      return true;
    } catch (error) {
      notifyError(parseApiError(error));
      return false;
    } finally {
      set({ loading: false });
    }
  },
  updateAccount: async (id, payload, includeInactive = false) => {
    set({ loading: true });
    try {
      await api.patch(`/accounts/${id}`, payload);
      notifyInfo("Cuenta actualizada");
      await useAccountStore.getState().fetchAccounts(includeInactive);
      return true;
    } catch (error) {
      notifyError(parseApiError(error));
      return false;
    } finally {
      set({ loading: false });
    }
  },
  deleteAccount: async (id, options) => {
    set({ loading: true });
    try {
      await api.delete(`/accounts/${id}`, {
        params: {
          force: options?.force ?? false,
          hard_delete: options?.hardDelete ?? false,
        },
      });
      notifyInfo("Cuenta eliminada");
      const response = await api.get<AccountSummaryApi[]>("/accounts", {
        params: options?.includeInactive ? { include_inactive: true } : undefined,
      });
      set({ accounts: response.data.map(normalizeSummary), selected: undefined });
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      set({ loading: false });
    }
  },
}));
