import { useEffect, useMemo, useState } from "react";
import { useReportStore } from "../store/reports";
import { useCategoriesStore } from "../store/categories";
import { useAccountStore } from "../store/accounts";
import { useTurnStore } from "../store/turns";
import { DatePicker } from "../components/DatePicker";
import { NavLink } from "react-router-dom";
import { api } from "../lib/api";
import { notifyError, notifyInfo } from "../ui/toast";

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

function AreaChart({ data }: { data: Array<{ date: string; net: number }> }) {
  if (!data.length) return null;
  const width = Math.max(data.length * 30, 500);
  const height = 200;
  const padding = 40;
  const graphWidth = width - 2 * padding;
  const graphHeight = height - 2 * padding;

  // Datos originales: neto diario
  const dailyNetValues = data.map(d => d.net);
  
  // Calcular neto acumulado (global)
  const cumulativeNetValues: number[] = [];
  let cum = 0;
  for (const d of data) {
    cum += d.net;
    cumulativeNetValues.push(cum);
  }

  // Determinar el máximo valor absoluto (considerando ambos conjuntos) para escalado
  const allValues = [...dailyNetValues, ...cumulativeNetValues];
  const max = Math.max(...allValues.map(Math.abs), 1);
  
  // Línea base Y (cero)
  const zeroY = padding + graphHeight / 2;
  // Rango usable arriba y abajo de la línea cero (dejar margen para las etiquetas)
  const usableHalfHeight = graphHeight * 0.4; // 80% del área total (40% arriba, 40% abajo)
  
  // Escala: mapea val (positivo o negativo) a coordenada Y
  // val positivo → y menor (arriba)
  // val negativo → y mayor (abajo)
  const scaleY = (val: number) => {
    return zeroY - (val / max) * usableHalfHeight;
  };

  const stepX = graphWidth / (data.length - 1 || 1);

  // Puntos para neto diario (área)
  const dailyPoints = data.map((d, i) => {
    const x = padding + i * stepX;
    const y = scaleY(d.net);
    return `${x},${y}`;
  }).join(" ");

  // Puntos para neto acumulado (línea)
  const cumulativePoints = cumulativeNetValues.map((val, i) => {
    const x = padding + i * stepX;
    const y = scaleY(val);
    return `${x},${y}`;
  }).join(" ");

  // Puntos para el área: desde la línea base hasta los puntos diarios
  const areaPoints = `${padding},${zeroY} ${dailyPoints} ${padding + graphWidth},${zeroY}`;

  return (
    <svg width={width} height={height} style={{ overflow: "visible" }}>
      <defs>
        <linearGradient id="netGradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="rgba(15, 118, 110, 0.4)" />
          <stop offset="100%" stopColor="rgba(15, 118, 110, 0.1)" />
        </linearGradient>
      </defs>
      {/* Línea base en cero */}
      <line x1={padding} y1={zeroY} x2={padding + graphWidth} y2={zeroY} stroke="#94a3b8" strokeDasharray="4" />
      
      {/* Área para neto diario (relleno verde) */}
      <polygon points={areaPoints} fill="url(#netGradient)" stroke="none" />
      
      {/* Polilínea para neto diario */}
      <polyline points={dailyPoints} fill="none" stroke="#0f766e" strokeWidth="2" />
      
      {/* Línea para neto acumulado (global) - color rojo punteado */}
      <polyline points={cumulativePoints} fill="none" stroke="#dc2626" strokeWidth="2" strokeDasharray="5,3" />

      {/* Etiquetas y puntos */}
      {data.map((d, i) => {
        const x = padding + i * stepX;
        const dailyY = scaleY(d.net);
        const cumulativeY = scaleY(cumulativeNetValues[i]);

        return (
          <g key={i}>
            {/* Puntos y etiquetas neto diario */}
            <circle cx={x} cy={dailyY} r="3" fill="#0f766e" />
            <text x={x} y={dailyY - 10} fontSize="9" fill="#0f766e" textAnchor="middle">{d.net >= 0 ? "+" : ""}{d.net.toFixed(0)}</text>
            
            {/* Puntos y etiquetas neto acumulado */}
            <circle cx={x} cy={cumulativeY} r="3" fill="#dc2626" />
            <text x={x} y={cumulativeY + 12} fontSize="9" fill="#dc2626" textAnchor="middle">{cumulativeNetValues[i] >= 0 ? "+" : ""}{cumulativeNetValues[i].toFixed(0)}</text>
            
            {/* Fecha en la parte inferior (una sola vez) */}
            <text x={x} y={height - 12} fontSize="9" fill="#64748b" textAnchor="middle">{new Date(d.date).toLocaleDateString("es-ES", { day: "2-digit", month: "2-digit" })}</text>
          </g>
        );
      })}
      
      {/* Leyenda */}
      <g transform={`translate(${padding}, 15)`}>
        <rect x="0" y="0" width="12" height="3" fill="#0f766e" />
        <text x="16" y="4" fontSize="10" fill="#333">Neto Diario</text>
        <rect x="80" y="0" width="12" height="3" fill="#dc2626" strokeDasharray="5,3" />
        <text x="96" y="4" fontSize="10" fill="#333">Neto Global</text>
      </g>
    </svg>
  );
}

export function ReportDashboard() {
  const { period, startDate, endDate, setPeriod, setDateRange, fetchMovements, movements, loading } = useReportStore();
  const { fetchActiveGlobal } = useTurnStore();
  const accounts = useAccountStore((state) => state.accounts);
  const fetchAccounts = useAccountStore((state) => state.fetchAccounts);
  const categories = useCategoriesStore((state) => state.categories);
  const getCategoryName = useCategoriesStore((state) => state.getNombreByCodigo);

  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  useEffect(() => { void fetchAccounts(); }, [fetchAccounts]);

  useEffect(() => {
    const loadData = async () => {
      // Actualizar el turno activo para mantener el store fresco (otros componentes lo usan)
      await fetchActiveGlobal();
      // Cargar movimientos SIN filtrar por turno: reporte por fecha, no por turno
      await fetchMovements();
    };
    void loadData();
  }, [fetchMovements, fetchActiveGlobal, startDate, endDate]);

   const totalLiquidity = useMemo(() => accounts.reduce((sum, a) => sum + a.account_amount, 0), [accounts]);
   const totalIncome = useMemo(() => movements.filter(m => m.type === "INGRESO").reduce((sum, m) => sum + m.amount, 0), [movements]);
   const totalExpense = useMemo(() => movements.filter(m => m.type === "EGRESO").reduce((sum, m) => sum + m.amount, 0), [movements]);
   const netResult = totalIncome - totalExpense;

  const categoryMap = useMemo(() => {
    const map = new Map<string, string>();
    categories.forEach(cat => map.set(cat.codigo, cat.nombre));
    return map;
  }, [categories]);

  const incomeByCategory = useMemo(() => {
    const map = new Map<string, number>();
    movements.forEach(m => {
      if (m.type === "INGRESO" && m.categoria_codigo) {
        const name = m.categoria_nombre ?? categoryMap.get(m.categoria_codigo) ?? m.categoria_codigo;
        map.set(name, (map.get(name) || 0) + m.amount);
      }
    });
    return Array.from(map.entries()).map(([name, value]) => ({ name, value, percentage: totalIncome > 0 ? (value / totalIncome) * 100 : 0 })).sort((a, b) => b.value - a.value);
  }, [movements, categoryMap, totalIncome]);

  const expenseByCategory = useMemo(() => {
    const map = new Map<string, number>();
    movements.forEach(m => {
      if (m.type === "EGRESO" && m.categoria_codigo) {
        const name = m.categoria_nombre ?? categoryMap.get(m.categoria_codigo) ?? m.categoria_codigo;
        map.set(name, (map.get(name) || 0) + m.amount);
      }
    });
    return Array.from(map.entries()).map(([name, value]) => ({ name, value, percentage: totalExpense > 0 ? (value / totalExpense) * 100 : 0 })).sort((a, b) => b.value - a.value);
  }, [movements, categoryMap, totalExpense]);

  const dailyNetFlow = useMemo(() => {
    const map = new Map<string, { income: number; expense: number }>();
    movements.forEach(m => {
      const day = m.timestamp.split("T")[0];
      const cur = map.get(day) || { income: 0, expense: 0 };
      if (m.type === "INGRESO") cur.income += m.amount;
      if (m.type === "EGRESO") cur.expense += m.amount;
      map.set(day, cur);
    });
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b)).map(([date, vals]) => ({ date, net: vals.income - vals.expense }));
  }, [movements]);

  const incomeColor = "#16a34a";
  const expenseColor = "#dc2626";

  const downloadBackup = async () => {
    try {
      const response = await api.get("/admin/backup", { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: "text/plain" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = `ferrega_backup_${new Date().toISOString().split("T")[0]}.sql`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      notifyInfo("Backup descargado");
    } catch (error) {
      notifyError("Error al generar backup");
    }
  };

  return (
    <>
      <Tooltip tooltip={tooltip} />
      <section className="card">
        <div className="page-header">
          <div>
            <h2 className="page-title">Dashboard de Reportes</h2>
            <p className="page-subtitle">Análisis de flujo de caja</p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className={`button ${period === "30d" ? "button-primary" : "button-ghost"}`} type="button" onClick={() => setPeriod("30d")}>30 días</button>
            <button className={`button ${period === "60d" ? "button-primary" : "button-ghost"}`} type="button" onClick={() => setPeriod("60d")}>60 días</button>
            <button className={`button ${period === "custom" ? "button-primary" : "button-ghost"}`} type="button" onClick={() => setPeriod("custom")}>Personalizado</button>
            <button onClick={downloadBackup} className="button button-primary" type="button">Descargar backup</button>
          </div>
        </div>

        <p style={{ color: "var(--ink-500)", fontSize: 14, marginBottom: 16 }}>
          Periodo: {startDate} al {endDate}
        </p>

        <div style={{ marginBottom: 24 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 16 }}>
            <NavLink to="/report/balance" className="button button-primary" style={{ padding: 16, textDecoration: "none", display: "block" }}>
              <div style={{ fontSize: 18, fontWeight: 600 }}>Balance General</div>
              <div style={{ fontSize: 12, color: "var(--ink-500)" }}>Estado de situación financiera</div>
            </NavLink>
            <NavLink to="/report/statement" className="button button-primary" style={{ padding: 16, textDecoration: "none", display: "block" }}>
              <div style={{ fontSize: 18, fontWeight: 600 }}>Estado de Resultados</div>
              <div style={{ fontSize: 12, color: "var(--ink-500)" }}>Ingresos y gastos del período</div>
            </NavLink>
          </div>
        </div>

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
          <p>Cargando...</p>
        ) : (
          <>
            <div className="metric-grid compact" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: 24 }}>
              <div className="metric">
                <div className="metric-label">Liquidez total</div>
                <div className="metric-value">{totalLiquidity.toFixed(2)}</div>
              </div>
              <div className="metric" style={{ "--color": "#16a34a" } as any}>
                <div className="metric-label">Total Ingresos</div>
                <div className="metric-value" style={{ color: "#16a34a" }}>{totalIncome.toFixed(2)}</div>
              </div>
              <div className="metric" style={{ "--color": "#dc2626" } as any}>
                <div className="metric-label">Total Egresos</div>
                <div className="metric-value" style={{ color: "#dc2626" }}>{totalExpense.toFixed(2)}</div>
              </div>
              <div className="metric">
                <div className="metric-label">Neto</div>
                <div className="metric-value" style={{ color: netResult >= 0 ? "#16a34a" : "#dc2626" }}>{netResult.toFixed(2)}</div>
              </div>
            </div>

            <h3 style={{ fontSize: 16, margin: "0 0 12px" }}>Flujo Neto Diario y Global</h3>
            <div style={{ marginBottom: 24 }}>
              <AreaChart data={dailyNetFlow} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 24 }}>
              <div className="card" style={{ padding: 16 }}>
                <h3 style={{ fontSize: 16, margin: "0 0 12px" }}>Ingresos por categoría</h3>
                <div style={{ display: "flex", gap: 16, alignItems: "center", minHeight: 140 }}>
                  {incomeByCategory.length > 0 ? (
                    <PieChart data={incomeByCategory} color={incomeColor} onHover={setTooltip} />
                  ) : (
                    <div style={{ color: "var(--ink-500)", fontStyle: "italic" }}>Sin datos</div>
                  )}
                  <div style={{ flex: 1, fontSize: 12 }}>
                    {incomeByCategory.map((cat, i) => (
                      <div key={i} style={{ display: "flex", gap: 6, marginBottom: 4 }}>
                        <span style={{ width: 10, height: 10, borderRadius: 2, background: incomeColor, flexShrink: 0 }}></span>
                        <span style={{ color: "var(--ink-700)", flex: 1 }}>{cat.name}</span>
                        <span style={{ fontWeight: 600 }}>{cat.value.toFixed(0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="card" style={{ padding: 16 }}>
                <h3 style={{ fontSize: 16, margin: "0 0 12px" }}>Egresos por categoría</h3>
                <div style={{ display: "flex", gap: 16, alignItems: "center", minHeight: 140 }}>
                  {expenseByCategory.length > 0 ? (
                    <PieChart data={expenseByCategory} color={expenseColor} onHover={setTooltip} />
                  ) : (
                    <div style={{ color: "var(--ink-500)", fontStyle: "italic" }}>Sin datos</div>
                  )}
                  <div style={{ flex: 1, fontSize: 12 }}>
                    {expenseByCategory.map((cat, i) => (
                      <div key={i} style={{ display: "flex", gap: 6, marginBottom: 4 }}>
                        <span style={{ width: 10, height: 10, borderRadius: 2, background: expenseColor, flexShrink: 0 }}></span>
                        <span style={{ color: "var(--ink-700)", flex: 1 }}>{cat.name}</span>
                        <span style={{ fontWeight: 600 }}>{cat.value.toFixed(0)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </section>
    </>
  );
}
