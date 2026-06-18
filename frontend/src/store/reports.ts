import { create } from "zustand";

import { api, parseApiError } from "../lib/api";
import { notifyError } from "../ui/toast";

export type ReportMovement = {
  id: string;
  type: "INGRESO" | "EGRESO" | "TRANSFERENCIA";
  amount: number;
  description: string | null;
  timestamp: string;
  account_id?: string;
  account_name?: string;
  categoria_codigo?: string | null;
  categoria_nombre?: string | null;
};

export type ReportPeriod = "30d" | "60d" | "custom";

export type ReportStore = {
  period: ReportPeriod;
  startDate: string;
  endDate: string;
  movements: ReportMovement[];
  loading: boolean;
  setPeriod: (period: ReportPeriod) => void;
  setDateRange: (startDate: string, endDate: string) => void;
  fetchMovements: (turnGroupId?: string) => Promise<void>;
  getTotalIncome: () => number;
  getTotalExpense: () => number;
  getNetResult: () => number;
};

const getDateRange = (period: ReportPeriod, customStart?: string, customEnd?: string) => {
  const end = customEnd ? new Date(customEnd) : new Date();
  const start = customStart ? new Date(customStart) : new Date();
  if (period !== "custom") {
    const days = period === "30d" ? 30 : 60;
    start.setTime(end.getTime() - days * 24 * 60 * 60 * 1000);
  }
  return {
    startDate: start.toISOString().split("T")[0],
    endDate: end.toISOString().split("T")[0],
  };
};

const defaultRange = getDateRange("30d");

export const useReportStore = create<ReportStore>((set, get) => ({
  period: "30d",
  startDate: defaultRange.startDate,
  endDate: defaultRange.endDate,
  movements: [],
  loading: false,

  setPeriod: (period) => {
    const { startDate, endDate } = getDateRange(period);
    set({ period, startDate, endDate });
  },

  setDateRange: (startDate, endDate) => {
    set({ period: "custom", startDate, endDate });
  },

   fetchMovements: async (turnGroupId?: string) => {
     const { startDate, endDate } = get();
     set({ loading: true });
     try {
       // Convertir fechas sin hora a datetime que cubra todo el día
       const startDateTime = `${startDate}T00:00:00.000Z`;
       const endDateTime = `${endDate}T23:59:59.999Z`;
       
       const params: any = {
         start_date: startDateTime,
         end_date: endDateTime,
       };
       if (turnGroupId) {
         params.turn_group_id = turnGroupId;
       }
       const response = await api.get("/movements/recent", { params });
       const rawItems: any[] = response.data?.items ?? [];
       const normalized: ReportMovement[] = rawItems.map((item) => ({
         id: item.id,
         type: item.type,
         amount: Number(item.amount),
         description: item.description ?? null,
         timestamp: item.timestamp,
         account_id: item.account_id ?? undefined,
         account_name: item.account_name ?? undefined,
        categoria_codigo: item.categoria_codigo ?? null,
         categoria_nombre: item.categoria_nombre ?? null,
       }));
       set({ movements: normalized, loading: false });
     } catch (error) {
       notifyError(parseApiError(error));
       set({ movements: [], loading: false });
     }
   },

   getTotalIncome: () => {
     return get().movements.reduce((sum, m) => m.type === "INGRESO" ? sum + m.amount : sum, 0);
   },

   getTotalExpense: () => {
     return get().movements.reduce((sum, m) => m.type === "EGRESO" ? sum + m.amount : sum, 0);
   },

  getNetResult: () => {
    return get().getTotalIncome() - get().getTotalExpense();
  },
}));
