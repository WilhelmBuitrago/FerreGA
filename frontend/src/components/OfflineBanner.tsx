import { useEffect, useState } from "react";

import { useSyncStore } from "../store/sync";

export function OfflineBanner() {
  const pendingCount = useSyncStore((state) => state.pendingCount);
  const refreshPending = useSyncStore((state) => state.refreshPending);
  const [online, setOnline] = useState(() => navigator.onLine);

  useEffect(() => {
    void refreshPending();
    const handleOnline = () => setOnline(true);
    const handleOffline = () => setOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [refreshPending]);

  if (online) return null;

  return (
    <div className="banner">
      <span>Estas sin conexion. {pendingCount} comandos pendientes.</span>
      <span>Se sincronizaran al volver.</span>
    </div>
  );
}
