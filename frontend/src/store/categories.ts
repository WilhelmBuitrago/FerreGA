import { create } from "zustand";

import { api } from "../lib/api";

export type Category = {
  codigo: string;
  nombre: string;
  tipo: "INGRESO" | "GASTO" | "PASIVO" | "ACTIVO" | "TRANSFERENCIA";
  grupo?: string | null;
};

export type CategoryGroup = {
  grupo: string;
  categories: Category[];
};

export type CategoriesStore = {
  categories: Category[];
  loading: boolean;
  fetchCategories: () => Promise<void>;
  getByTipo: (tipo: "INGRESO" | "GASTO") => Category[];
  getGroupedByTipo: (tipo: "INGRESO" | "GASTO") => CategoryGroup[];
};

export const useCategoriesStore = create<CategoriesStore>((set, get) => ({
  categories: [],
  loading: false,
  fetchCategories: async () => {
    set({ loading: true });
    try {
      const response = await api.get<{ categories: Category[] }>("/categories");
      set({ categories: response.data.categories, loading: false });
    } catch (error) {
      console.error("Failed to fetch categories", error);
      set({ loading: false });
    }
  },
  getByTipo: (tipo) => {
    return get().categories.filter((cat) => cat.tipo === tipo);
  },
  getGroupedByTipo: (tipo) => {
    const cats = get().getByTipo(tipo);
    const groups: Record<string, Category[]> = {};
    cats.forEach((cat) => {
      const groupName = cat.grupo || "Sin grupo";
      if (!groups[groupName]) groups[groupName] = [];
      groups[groupName].push(cat);
    });
    return Object.entries(groups).map(([grupo, categories]) => ({ grupo, categories }));
  },
  getNombreByCodigo: (codigo: string) => {
    const cat = get().categories.find((c) => c.codigo === codigo);
    return cat?.nombre ?? codigo;
  },
}));
