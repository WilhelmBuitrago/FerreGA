import { create } from "zustand";
import { api } from "../lib/api";
import { useMovementStore } from "./movements";
import { useCreditStore } from "./credits";
import { useCategoriesStore } from "./categories";
import { notifyError, notifyInfo } from "../ui/toast";

export type UsageStats = {
  minute_requests: number;
  day_requests: number;
  day_tokens: number;
  rpm_limit: number;
  rpd_limit: number;
  tpd_limit: number;
};

export type WhisperUsage = {
  minute_requests: number;
  day_requests: number;
  hour_seconds: number;
  day_seconds: number;
  rpm_limit: number;
  rpd_limit: number;
  ash_limit: number;
  asd_limit: number;
};

export type Movement =
  | { movement_type: "ingreso"; movement: { account_id: string; amount: number; categoria_codigo: string; description?: string | null } }
  | { movement_type: "egreso"; movement: { account_id: string; amount: number; categoria_codigo: string; description?: string | null } }
  | { movement_type: "transferencia"; movement: { source_account_id: string; target_account_id: string; amount: number; description?: string | null } }
  | { movement_type: "credito"; movement: { type: string; total_amount: number; due_date: string; description?: string | null } };

export type ParseResponse = {
  movement_type: string;
  movement: any;
  usage: UsageStats;
};

export type Message = {
  id: string;
  text: string;
  sender: "user" | "bot";
  timestamp: number;
  parsed?: ParseResponse | null;
  error?: string | null;
  cancelled?: boolean; // marca si la propuesta fue cancelada
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AIStore = {
  isOpen: boolean;
  messages: Message[];
  isLoading: boolean;
  whisperUsage: WhisperUsage | null;
  chatUsage: UsageStats | null;
  openModal: () => void;
  closeModal: () => void;
  sendMessage: (text: string) => Promise<void>;
  confirmParsed: () => Promise<void>;
  cancelParsed: () => void;
  reset: () => void;
  setWhisperUsage: (usage: WhisperUsage) => void;
  setChatUsage: (usage: UsageStats) => void;
  fetchUsage: () => Promise<void>;
};

export const useAIStore = create<AIStore>((set, get) => ({
  isOpen: false,
  messages: [],
  isLoading: false,
  whisperUsage: null,
  chatUsage: null,

  openModal: () => {
    set({ isOpen: true });
    // Add welcome message if none
    const state = get();
    if (state.messages.length === 0) {
      const welcome: Message = {
        id: crypto.randomUUID(),
        text: "Hola, ¿qué puedo hacer por ti hoy?",
        sender: "bot",
        timestamp: Date.now(),
      };
      set({ messages: [welcome] });
    }
    // Fetch current usage from backend
    get().fetchUsage();
  },

  closeModal: () => {
    // Reset chat when closing
    set({ isOpen: false, messages: [], isLoading: false });
  },

  reset: () => {
    set({ messages: [], isLoading: false });
  },

  fetchUsage: async () => {
    try {
      const response = await api.get<{ chat: UsageStats; whisper: WhisperUsage }>("/ai/usage");
      set({ chatUsage: response.data.chat, whisperUsage: response.data.whisper });
    } catch (error) {
      console.error("Failed to fetch usage:", error);
      // En caso de error, no tocamos los valores actuales
    }
  },

  sendMessage: async (text: string) => {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      text,
      sender: "user",
      timestamp: Date.now(),
    };

    set((state) => ({
      messages: [...state.messages, userMessage],
      isLoading: true,
    }));

    try {
      // Build context from last few messages (excluding the current user message just added)
      const state = get();
      const contextMessages: ChatMessage[] = state.messages
        .slice(-6) // last 6 messages (3 pairs)
        .filter(m => !m.error) // exclude error messages
        .map(m => ({
          role: m.sender === "user" ? "user" : "assistant",
          content: m.sender === "bot" && m.parsed
            ? `[Propuesta]: ${JSON.stringify(m.parsed.movement)}`
            : m.text,
        }));

  const response = await api.post<ParseResponse>("/ai/parse", {
    text,
    context: contextMessages,
  });

      // Guardar el usage de Groq para el panel
      get().setChatUsage(response.data.usage);

      const botMessage: Message = {
        id: crypto.randomUUID(),
        text: "Confirmá estos datos:",
        sender: "bot",
        timestamp: Date.now(),
        parsed: response.data,
      };

      set((state) => ({
        messages: [...state.messages, botMessage],
        isLoading: false,
      }));
    } catch (error: any) {
      const errorDetail = error?.response?.data?.detail || error?.message || "No pude entender el mensaje. Por favor usá el formulario manual.";
      const botMessage: Message = {
        id: crypto.randomUUID(),
        text: errorDetail,
        sender: "bot",
        timestamp: Date.now(),
        error: "parse_failed",
      };

      set((state) => ({
        messages: [...state.messages, botMessage],
        isLoading: false,
      }));
    }
  },

  confirmParsed: async () => {
    const { messages } = get();
    const lastMessage = messages[messages.length - 1];

    if (!lastMessage?.parsed) {
      notifyError("No hay datos para confirmar");
      return;
    }

    const movementType = lastMessage.parsed.movement_type as "ingreso" | "egreso" | "transferencia" | "credito";
    const movement = lastMessage.parsed.movement as any;

    let success = false;
    let successText = "";

    try {
      if (movementType === "ingreso") {
        const { addIncome } = useMovementStore.getState();
        await addIncome({
          account_id: movement.account_id,
          amount: movement.amount,
          description: movement.description || undefined,
          categoria_codigo: movement.categoria_codigo,
        });
        successText = "Ingreso registrado con IA";
      } else if (movementType === "egreso") {
        const { addExpense } = useMovementStore.getState();
        await addExpense({
          account_id: movement.account_id,
          amount: movement.amount,
          description: movement.description || undefined,
          categoria_codigo: movement.categoria_codigo,
        });
        successText = "Egreso registrado con IA";
      } else if (movementType === "transferencia") {
        const { addTransfer } = useMovementStore.getState();
        await addTransfer({
          source_account_id: movement.source_account_id,
          target_account_id: movement.target_account_id,
          amount: movement.amount,
          description: movement.description || undefined,
        });
        successText = "Transferencia registrada con IA";
      } else if (movementType === "credito") {
        const { createCredit } = useCreditStore.getState();
        await createCredit({
          type: movement.type,
          total_amount: movement.total_amount,
          due_date: movement.due_date,
          description: movement.description || undefined,
        });
        successText = "Crédito registrado con IA";
      } else {
        notifyError("Tipo de movimiento no reconocido");
        return;
      }
      success = true;
    } catch (err) {
      notifyError("Error al registrar: " + (err instanceof Error ? err.message : String(err)));
      return;
    } finally {
      if (success) {
        const successMessage: Message = {
          id: crypto.randomUUID(),
          text: `✅ ${successText}`,
          sender: "bot",
          timestamp: Date.now(),
        };
        set((state) => ({
          messages: [...state.messages.filter(m => m.id !== lastMessage.id), successMessage],
        }));
        notifyInfo(successText);
      }
    }
  },

  cancelParsed: () => {
    const { messages } = get();
    const lastBotWithParsed = [...messages].reverse().find(m => m.sender === "bot" && m.parsed);
    if (lastBotWithParsed) {
      set((state) => ({
        messages: state.messages.map(m =>
          m.id === lastBotWithParsed!.id
            ? { ...m, cancelled: true, parsed: undefined }
            : m
        ),
      }));
    }
  },

  setWhisperUsage: (usage) => set({ whisperUsage: usage }),

  setChatUsage: (usage) => set({ chatUsage: usage }),
}));
