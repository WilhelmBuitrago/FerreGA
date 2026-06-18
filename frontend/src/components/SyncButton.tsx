import { useSyncStore } from "../store/sync";

export function SyncButton() {
  const syncing = useSyncStore((state) => state.syncing);
  const syncNow = useSyncStore((state) => state.syncNow);

  return (
    <button className="button button-ghost" type="button" onClick={() => void syncNow()} disabled={syncing}>
      {syncing ? "Sincronizando..." : "Sincronizar"}
    </button>
  );
}
