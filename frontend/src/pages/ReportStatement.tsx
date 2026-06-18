import { useEffect, useMemo, useState } from "react";
import { useReportStore } from "../store/reports";
import { useCategoriesStore } from "../store/categories";
import { useTurnStore } from "../store/turns";
import { DatePicker } from "../components/DatePicker";

interface TooltipData {
  x: number;
  y: number;
  name: string;
  value: number;
  percentage: number;
}

function PieChart({ data, color, onHover }: { data: Array<{ name: string; value: number; percentage: number }>; color: string; onHover?: (d: TooltipData | null) => void }) {
  if (!data.length) return null;
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const isFullCircle = data.length === 1;

  if (isFullCircle) {
    const d = data[0];
    return (
      <svg width={120} height={120} viewBox="0 0 100 100" style={{ flexShrink: 0 }}>
        <circle
          cx="50"
          cy="50"
          r="40"
          fill={color}
          stroke="#fff"
          strokeWidth="1"
          style={{ cursor: "pointer" }}
          onMouseEnter={(e) => onHover?.({ x: e.clientX, y: e.clientY, name: d.name, value: d.value, percentage: d.percentage })}
          onMouseLeave={() => onHover?.(null)}
        />
        <circle cx="50" cy="50" r="25" fill="white" />
      </svg>
    );
  }

  let cumulative = 0;
  const slices = data.map((d) => {
    const startAngle = (cumulative / total) * 360;
    cumulative += d.value;
    const endAngle = (cumulative / total) * 360;
    const startRad = (startAngle - 90) * (Math.PI / 180);
    const endRad = (endAngle - 90) * (Math.PI / 180);
    const r = 40;
    const x1 = 50 + r * Math.cos(startRad);
    const y1 = 50 + r * Math.sin(startRad);
    const x2 = 50 + r * Math.cos(endRad);
    const y2 = 50 + r * Math.sin(endRad);
    const largeArc = endAngle - startAngle > 180 ? 1 : 0;
    const pathData = `M 50 50 L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
    return { path: pathData, name: d.name, value: d.value, percentage: d.percentage };
  });

  return (
    <svg width={120} height={120} viewBox="0 0 100 100">
      {slices.map((s, i) => (
        <path
          key={i}
          d={s.path}
          fill={color}
          stroke="#fff"
          strokeWidth="1"
          style={{ cursor: "pointer" }}
          onMouseEnter={(e) => onHover?.({ x: e.clientX, y: e.clientY, name: s.name, value: s.value, percentage: s.percentage })}
          onMouseLeave={() => onHover?.(null)}
        />
      ))}
      <circle cx="50" cy="50" r="25" fill="white" />
    </svg>
  );
}

function Tooltip({ tooltip }: { tooltip: TooltipData | null }) {
  if (!tooltip) return null;
  return (
    <div style={{ position: "fixed", left: tooltip.x + 12, top: tooltip.y + 12, background: "rgba(15,23,42,0.95)", color: "#fff", padding: "8px 12px", borderRadius: 8, fontSize: 13, zIndex: 10000, pointerEvents: "none" }}>
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{tooltip.name}</div>
      <div>Valor: {tooltip.value.toFixed(2)}</div>
      <div>Porcentaje: {tooltip.percentage.toFixed(1)}%</div>
    </div>
  );
}

export function ReportStatement() {
  const { period, startDate, endDate, setPeriod, setDateRange, fetchMovements, movements, loading } = useReportStore();
  const { fetchActiveGlobal } = useTurnStore();
  const categories = useCategoriesStore((state) => state.categories);

  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  useEffect(() => {
    const loadData = async () => {
      // Actualizar el turno activo para mantener el store fresco (otros componentes lo usan)
      await fetchActiveGlobal();
      // Cargar movimientos SIN filtrar por turno: reporte por fecha, no por turno
      await fetchMovements();
    };
    void loadData();
  }, [fetchMovements, fetchActiveGlobal, startDate, endDate]);

  const totalIncome = useMemo(() => movements.filter(m => m.type === "INGRESO").reduce((sum, m) => sum + m.amount, 0), [movements]);
  const totalExpense = useMemo(() => movements.filter(m => m.type === "EGRESO").reduce((sum, m) => sum + m.amount, 0), [movements]);
  const netResult = totalIncome - totalExpense;

  const incomeCategoriesMap = useMemo(() => {
    const map = new Map<string, { nombre: string; grupo?: string }>();
    categories.forEach(cat => {
      if (cat.tipo === "INGRESO") {
        map.set(cat.codigo, { nombre: cat.nombre, grupo: cat.grupo });
      }
    });
    return map;
  }, [categories]);

  const expenseCategoriesMap = useMemo(() => {
    const map = new Map<string, { nombre: string; grupo?: string }>();
    categories.forEach(cat => {
      if (cat.tipo === "GASTO") {
        map.set(cat.codigo, { nombre: cat.nombre, grupo: cat.grupo });
      }
    });
    return map;
  }, [categories]);

  const incomeByGroup = useMemo(() => {
    const groups = new Map<string, { nombre?: string; items: Array<{nombre: string, value: number}>, total: number }>();
    
    movements.forEach(m => {
      if (m.type === "INGRESO" && m.categoria_codigo) {
        const cat = incomeCategoriesMap.get(m.categoria_codigo);
        const groupKey = cat?.grupo || "Otros Ingresos";
        const catName = m.categoria_nombre || cat?.nombre || m.categoria_codigo;
        
        if (!groups.has(groupKey)) {
          groups.set(groupKey, { nombre: groupKey, items: [], total: 0 });
        }
        const group = groups.get(groupKey)!;
        const existing = group.items.find(i => i.nombre === catName);
        if (existing) {
          existing.value += m.amount;
        } else {
          group.items.push({ nombre: catName, value: m.amount });
        }
        group.total += m.amount;
      }
    });
    
    return Array.from(groups.values())
      .map(g => ({
        group: g.nombre || "Sin grupo",
        items: g.items.sort((a,b) => b.value - a.value),
        total: g.total
      }))
      .sort((a,b) => a.group.localeCompare(b.group));
  }, [movements, incomeCategoriesMap]);

  const expenseByGroup = useMemo(() => {
    const groups = new Map<string, { nombre?: string; items: Array<{nombre: string, value: number}>, total: number }>();
    
    movements.forEach(m => {
      if (m.type === "EGRESO" && m.categoria_codigo) {
        const cat = expenseCategoriesMap.get(m.categoria_codigo);
        const groupKey = cat?.grupo || "Otros Gastos";
        const catName = m.categoria_nombre || cat?.nombre || m.categoria_codigo;
        
        if (!groups.has(groupKey)) {
          groups.set(groupKey, { nombre: groupKey, items: [], total: 0 });
        }
        const group = groups.get(groupKey)!;
        const existing = group.items.find(i => i.nombre === catName);
        if (existing) {
          existing.value += m.amount;
        } else {
          group.items.push({ nombre: catName, value: m.amount });
        }
        group.total += m.amount;
      }
    });
    
    return Array.from(groups.values())
      .map(g => ({
        group: g.nombre || "Sin grupo",
        items: g.items.sort((a,b) => b.value - a.value),
        total: g.total
      }))
      .sort((a,b) => a.group.localeCompare(b.group));
  }, [movements, expenseCategoriesMap]);

  const renderCascadingSection = (title: string, groups: typeof incomeByGroup, total: number) => (
    <div style={{ marginBottom: 24 }}>
      <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 16 }}>{title}</div>
      {groups.length === 0 ? (
        <div style={{ paddingLeft: 16, color: "var(--ink-500)", fontStyle: "italic", fontSize: 14 }}>
          No hay {title.toLowerCase()} registrados
        </div>
      ) : (
        groups.map(g => (
          <div key={g.group} style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 500, marginBottom: 4, paddingLeft: 12 }}>{g.group}</div>
            {g.items.map(item => (
              <div key={item.nombre} style={{ display: "flex", justifyContent: "space-between", padding: "2px 0", fontSize: 14, paddingLeft: 24 }}>
                <span>{item.nombre}</span>
                <span>{item.value.toFixed(2)}</span>
              </div>
            ))}
            <div style={{ paddingLeft: 24, borderTop: "1px solid var(--border)", marginTop: 4, fontWeight: 600, display: "flex", justifyContent: "flex-end" }}>
              Subtotal {g.group}: {g.total.toFixed(2)}
            </div>
          </div>
        ))
      )}
      <div style={{ fontWeight: 600, display: "flex", justifyContent: "space-between", paddingTop: 8, borderTop: "2px solid var(--border)" }}>
        <span>Total {title}</span>
        <span>{total.toFixed(2)}</span>
      </div>
    </div>
  );

  return (
    <>
      <Tooltip tooltip={tooltip} />
      <section className="card">
        <div className="page-header">
          <div>
            <h2 className="page-title">Estado de Resultados</h2>
            <p className="page-subtitle">Ingresos y gastos del período</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className={`button ${period === "30d" ? "button-primary" : "button-ghost"}`} type="button" onClick={() => setPeriod("30d")}>30 días</button>
            <button className={`button ${period === "60d" ? "button-primary" : "button-ghost"}`} type="button" onClick={() => setPeriod("60d")}>60 días</button>
            <button className={`button ${period === "custom" ? "button-primary" : "button-ghost"}`} type="button" onClick={() => setPeriod("custom")}>Personalizado</button>
          </div>
        </div>

        <p style={{ color: "var(--ink-500)", fontSize: 14, marginBottom: 16 }}>
          Periodo: {startDate} al {endDate}
        </p>

        {period === "custom" && (
          <div style={{ display: "flex", gap: 12, alignItems: "flex-end", marginBottom: 16 }}>
            <div>
              <label>Desde</label>
              <DatePicker value={startDate} onChange={(iso) => setDateRange(iso, endDate)} />
            </div>
            <div>
              <label>Hasta</label>
              <DatePicker value={endDate} onChange={(iso) => setDateRange(startDate, iso)} />
            </div>
          </div>
        )}

        {loading ? (
          <p>Cargando movimientos...</p>
        ) : (
          <>
            <div style={{ marginBottom: 24 }}>
              {renderCascadingSection("Ingresos", incomeByGroup, totalIncome)}
              {renderCascadingSection("Gastos", expenseByGroup, totalExpense)}
              
              <div style={{ borderTop: "2px solid var(--border)", paddingTop: 16 }}>
                <div style={{ fontSize: 18, fontWeight: 600, display: "flex", justifyContent: "space-between" }}>
                  <span>Resultado Neto del Período</span>
                  <span style={{ color: netResult >= 0 ? "#16a34a" : "#dc2626" }}>{netResult.toFixed(2)}</span>
                </div>
              </div>
            </div>
          </>
        )}
      </section>
    </>
  );
}
