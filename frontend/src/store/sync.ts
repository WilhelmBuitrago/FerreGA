import { create } from "zustand";

import {
  type Command,
  type CommandType,
  countPendingCommands,
  enqueueCommand,
  listPendingCommands,
  removeCommand,
  updateCommand,
} from "../lib/commandQueue";
import { api, isOffline, parseApiError } from "../lib/api";
import { useAccountStore } from "./accounts";
import { notifyError, notifyInfo } from "../ui/toast";

const MAX_BATCH = 50;

export type SyncStore = {
  pendingCount: number;
  syncing: boolean;
  refreshPending: () => Promise<void>;
  enqueue: (command: { type: CommandType; payload: Record<string, unknown> }) => Promise<Command>;
  syncNow: () => Promise<void>;
};

export const useSyncStore = create<SyncStore>((set, get) => ({
  pendingCount: 0,
  syncing: false,
  refreshPending: async () => {
    const count = await countPendingCommands();
    set({ pendingCount: count });
  },
  enqueue: async (command) => {
    const providedKey = command.payload.idempotency_key;
    const idempotency_key =
      typeof providedKey === "string"
        ? providedKey
        : "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${Date.now()}`;
    const record = await enqueueCommand({
      type: command.type,
      payload: { ...command.payload, idempotency_key },
      idempotency_key,
    });
    await get().refreshPending();
    return record;
  },
  syncNow: async () => {
    if (isOffline()) return;
    if (get().syncing) return;
    set({ syncing: true });
    try {
      const pending = await listPendingCommands();
      if (!pending.length) return;

      const batch = pending.slice(0, MAX_BATCH);
      const response = await api.post("/sync", {
        commands: batch.map((command) => ({
          id: command.id,
          type: command.type,
          payload: command.payload,
          timestamp: command.timestamp,
          idempotency_key: command.idempotency_key,
        })),
      });

      const results = (response.data as { results: { command_id: string; status: string; error?: string }[] })
        .results;

      for (const command of batch) {
        const result = results.find((entry) => entry.command_id === command.id);
        if (!result) continue;
        if (result.status === "processed") {
          await removeCommand(command.id);
          notifyInfo("Comando sincronizado");
        } else {
          const nextAttempts = command.attempts + 1;
          const shouldRetry = nextAttempts < 3;
          const nextAttemptAt = new Date(
            Date.now() + Math.pow(2, nextAttempts) * 1000
          ).toISOString();
          const updated: Command = {
            ...command,
            status: shouldRetry ? "pending" : "failed",
            attempts: nextAttempts,
            next_attempt_at: shouldRetry ? nextAttemptAt : undefined,
          };
          await updateCommand(updated);
          notifyError(result.error ?? "Error al sincronizar comando");
        }
      }
      await useAccountStore.getState().fetchAccounts();
    } catch (error) {
      notifyError(parseApiError(error));
    } finally {
      set({ syncing: false });
      await get().refreshPending();
    }
  },
}));
