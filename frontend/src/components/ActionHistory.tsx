import { useState, useEffect, useCallback } from "react";

import { api } from "../lib/api";
import { useAccountStore } from "../store/accounts";
import { useCategoriesStore } from "../store/categories";
import { notifyError } from "../ui/toast";

type MovementType = "INCOME" | "EXPENSE" | "TRANSFER";

interface MovementItem {
  id: string;
  type: MovementType;
  amount: number;
  description: string | null;
  timestamp: string;
  turn_id: string;
  turn_group_id: string;
  account_id?: string;
  account_name?: string;
  is_outgoing?: boolean;
  source_account_name?: string;
  target_account_name?: string;
}

interface Filters {
  type: MovementType | "";
  amountMin: number | "";
  amountMax: number | "";
  descriptionRegex: string;
  accountId: string;
}

interface ActionHistoryProps {
  turnGroupId?: string;
  accountId?: string;
}

export function ActionHistory({ turnGroupId, accountId: propAccountId }: ActionHistoryProps) {
  const accounts = useAccountStore((state) => state.accounts);
  const getCategoryName = useCategoriesStore((state) => state.getNombreByCodigo);
  const [movements, setMovements] = useState<MovementItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [skip, setSkip] = useState(0);
  const [limit] = useState(50);
  const [hasMore, setHasMore] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [localAccountId, setLocalAccountId] = useState(propAccountId ?? "");
  const [filters, setFilters] = useState<Filters>({
    type: "",
    amountMin: "",
    amountMax: "",
    descriptionRegex: "",
    accountId: propAccountId ?? "",
  });

  // Sincronizar accountId desde props
  useEffect(() => {
    if (propAccountId !== undefined) {
      setLocalAccountId(propAccountId);
    }
  }, [propAccountId]);

  const fetchMovements = useCallback(async (isLoadMore: boolean = false) => {
    setLoading(true);
    try {
      const currentSkip = isLoadMore ? skip : 0;
      const params: any = {
        limit,
        skip: currentSkip,
      };
      if (turnGroupId) {
        params.turn_group_id = turnGroupId;
      }
      if (localAccountId) {
        params.account_id = localAccountId;
      }
      if (filters.type) params.movement_type = filters.type;
      if (filters.amountMin !== "") params.amount_min = filters.amountMin;
      if (filters.amountMax !== "") params.amount_max = filters.amountMax;
      if (filters.descriptionRegex) params.description_regex = filters.descriptionRegex;

      const response = await api.get("/movements/recent", { params });
      const rawItems: any[] = response.data?.items ?? [];

      const normalizedItems = rawItems.map((item) => ({
        ...item,
        amount: Number(item.amount),
        turn_id: item.turn_id,
        turn_group_id: item.turn_group_id,
        account_id: item.account_id,
        account_name: item.account_name,
        is_outgoing: item.is_outgoing,
        categoria_codigo: item.categoria_codigo ?? null,
      }));

      const combined: MovementItem[] = [];
      const transferMap = new Map<string, { outgoing: any; incoming: any }>();

      for (const item of normalizedItems) {
        if (item.type === "TRANSFER") {
          const key = `${item.turn_group_id}-${item.amount}-${item.description}`;
          if (!transferMap.has(key)) {
            transferMap.set(key, { outgoing: null, incoming: null });
          }
          const entry = transferMap.get(key)!;
          if (item.is_outgoing) {
            entry.outgoing = item;
          } else {
            entry.incoming = item;
          }
        } else {
          combined.push(item as MovementItem);
        }
      }

      for (const { outgoing, incoming } of transferMap.values()) {
        if (outgoing && incoming) {
          combined.push({
            id: `transfer-${outgoing.id}-${incoming.id}`,
            type: "TRANSFER",
            amount: outgoing.amount,
            description: outgoing.description || "Transferencia",
            timestamp: incoming.timestamp,
            turn_id: outgoing.turn_id,
            turn_group_id: outgoing.turn_group_id,
            source_account_name: outgoing.account_name,
            target_account_name: incoming.account_name,
            is_outgoing: false,
          } as MovementItem);
        } else if (outgoing) {
          combined.push({
            ...outgoing,
            id: outgoing.id,
            source_account_name: outgoing.account_name,
            target_account_name: null,
            is_outgoing: true,
          } as MovementItem);
        } else if (incoming) {
          combined.push({
            ...incoming,
            id: incoming.id,
            source_account_name: null,
            target_account_name: incoming.account_name,
            is_outgoing: false,
          } as MovementItem);
        }
      }

      combined.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

      if (isLoadMore) {
        setMovements((prev) => [...prev, ...combined]);
      } else {
        setMovements(combined);
      }
      setHasMore(combined.length === limit);
      setSkip((prev) => prev + combined.length);
    } catch (error) {
      notifyError("Error cargando historial");
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [turnGroupId, localAccountId, filters, limit, skip]);

  useEffect(() => {
    setSkip(0);
    setMovements([]);
    void fetchMovements(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [turnGroupId, localAccountId, filters]);

  const getMovementClass = (type: MovementType) => {
    switch (type) {
      case "INCOME":
        return "income";
      case "EXPENSE":
        return "expense";
      case "TRANSFER":
        return "transfer";
      default:
        return "";
    }
  };

  const getTypeLabel = (item: MovementItem) => {
    if (item.type === "TRANSFER") {
      if (item.source_account_name && item.target_account_name) {
        return `Transferencia: ${item.source_account_name} → ${item.target_account_name}`;
      }
      if (item.is_outgoing) {
        return "Transferencia (salida)";
      }
      return "Transferencia (entrada)";
    }
    switch (item.type) {
      case "INCOME":
        return "Ingreso";
      case "EXPENSE":
        return "Egreso";
      default:
        return item.type;
    }
  };

  const handleFilterChange = (key: keyof Filters, value: string | number) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const clearFilters = () => {
    setFilters({
      type: "",
      amountMin: "",
      amountMax: "",
      descriptionRegex: "",
      accountId: localAccountId,
    });
  };

  return (
    <div className="card action-history">
      <div className="page-header">
        <div>
          <h3 className="page-title">Historial de acciones</h3>
          <p className="page-subtitle">{movements.length} registros</p>
        </div>
        <button
          className="button button-secondary fab-filter"
          type="button"
          onClick={() => setShowFilters(true)}
          title="Filtrar historial"
        >
          🔍 Filtrar
        </button>
      </div>

      {loading && movements.length === 0 ? (
        <p>Cargando...</p>
      ) : movements.length === 0 && !loading ? (
        <p>No hay movimientos registrados.</p>
      ) : (
        <div style={{ maxHeight: 500, overflowY: "auto" }}>
          <ul className="movement-list">
            {movements.map((movement) => (
               <li key={movement.id} className={`movement-item ${getMovementClass(movement.type)}`}>
                 <div className="movement-header">
                   <span className={`movement-type-badge ${getMovementClass(movement.type)}`}>
                     {getTypeLabel(movement)}
                   </span>
                   <span className="movement-amount">
                     {movement.type === "EXPENSE" ? "-" : ""}
                     {movement.amount.toFixed(2)}
                   </span>
                 </div>
                 <div className="movement-description">
                   {movement.description ?? "-"}
                   {movement.categoria_codigo && (
                     <span className="movement-category" style={{ fontSize: "0.85em", color: "#666", marginLeft: 8 }}>
                       [{getCategoryName(movement.categoria_codigo!)}]
                     </span>
                   )}
                 </div>
                 <div className="movement-meta">
                   {new Date(movement.timestamp).toLocaleDateString("es-ES")} {new Date(movement.timestamp).toLocaleTimeString("es-ES", { hour: '2-digit', minute: '2-digit' })}
                   {!localAccountId && movement.account_id && ` • Cuenta: ${movement.account_name || movement.account_id.slice(0, 8)}...`}
                 </div>
               </li>
            ))}
          </ul>
        </div>
      )}

      {loading && movements.length > 0 && (
        <p style={{ textAlign: "center", marginTop: 8 }}>Cargando más...</p>
      )}

      {hasMore && movements.length > 0 && !loading && (
        <div style={{ textAlign: "center", marginTop: 12 }}>
          <button className="button button-ghost" type="button" onClick={() => fetchMovements(true)}>
            Cargar más
          </button>
        </div>
      )}

      {showFilters && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={() => setShowFilters(false)}>
          <div className="modal filter-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Filtrar historial</h3>
            <div className="form-grid">
              <label>
                Cuenta
                <select
                  value={localAccountId}
                  onChange={(e) => {
                    setLocalAccountId(e.target.value);
                    setFilters((prev) => ({ ...prev, accountId: e.target.value }));
                  }}
                >
                  <option value="">Todas las cuentas</option>
                  {accounts.map((acc) => (
                    <option key={acc.id} value={acc.id}>{acc.name}</option>
                  ))}
                </select>
              </label>
              <label>
                Tipo de movimiento
                <select
                  value={filters.type}
                  onChange={(e) => handleFilterChange("type", e.target.value as MovementType | "")}
                >
                  <option value="">Todos</option>
                  <option value="INCOME">Ingreso</option>
                  <option value="EXPENSE">Egreso</option>
                  <option value="TRANSFER">Transferencia</option>
                </select>
              </label>
              <label>
                Monto mínimo
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={filters.amountMin}
                  onChange={(e) => handleFilterChange("amountMin", e.target.value === "" ? "" : Number(e.target.value))}
                  placeholder="0.00"
                />
              </label>
              <label>
                Monto máximo
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={filters.amountMax}
                  onChange={(e) => handleFilterChange("amountMax", e.target.value === "" ? "" : Number(e.target.value))}
                  placeholder="Sin límite"
                />
              </label>
              <label>
                Buscar en descripción
                <input
                  type="text"
                  value={filters.descriptionRegex}
                  onChange={(e) => handleFilterChange("descriptionRegex", e.target.value)}
                  placeholder="Expresión regular"
                />
              </label>
            </div>
            <div className="modal-actions">
              <button className="button button-ghost" type="button" onClick={clearFilters}>
                Limpiar
              </button>
              <button className="button button-primary" type="button" onClick={() => setShowFilters(false)}>
                Aplicar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
