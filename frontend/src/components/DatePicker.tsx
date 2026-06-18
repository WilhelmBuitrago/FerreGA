import React, { useState, useEffect, useRef } from "react";

type DatePickerProps = {
  value: string; // ISO "YYYY-MM-DD" o ""
  onChange: (iso: string) => void;
  min?: string; // ISO YYYY-MM-DD opcional
};

export function DatePicker({ value, onChange, min }: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const [display, setDisplay] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  // Convertir ISO a dd/mm/aaaa
  const toDisplay = (iso: string) => {
    if (!iso) return "";
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
  };

  // Convertir dd/mm/aaaa a ISO
  const toISO = (text: string) => {
    const match = text.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
    if (!match) return null;
    const [, dd, mm, yyyy] = match;
    // validación básica de fecha
    const d = new Date(Number(yyyy), Number(mm) - 1, Number(dd));
    if (
      d.getFullYear() !== Number(yyyy) ||
      d.getMonth() !== Number(mm) - 1 ||
      d.getDate() !== Number(dd)
    ) {
      return null;
    }
    return `${yyyy}-${String(mm).padStart(2, "0")}-${String(dd).padStart(2, "0")}`;
  };

  useEffect(() => {
    setDisplay(toDisplay(value));
  }, [value]);

  // Cerrar al hacer clic fuera
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const text = e.target.value;
    setDisplay(text);
    const iso = toISO(text);
    if (iso) {
      onChange(iso);
    }
  };

  const handleSelectDay = (day: number) => {
    const y = viewDate.year;
    const m = String(viewDate.month + 1).padStart(2, "0");
    const d = String(day).padStart(2, "0");
    const iso = `${y}-${m}-${d}`;
    onChange(iso);
    setDisplay(toDisplay(iso));
    setOpen(false);
  };

  const today = new Date();
  const [viewDate, setViewDate] = useState({
    month: value ? parseInt(value.split("-")[1]) - 1 : today.getMonth(),
    year: value ? parseInt(value.split("-")[0]) : today.getFullYear(),
  });

  const changeMonth = (delta: number) => {
    setViewDate((prev) => {
      const d = new Date(prev.year, prev.month + delta);
      return { month: d.getMonth(), year: d.getFullYear() };
    });
  };

  const monthNames = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
  ];

  const year = viewDate.year;
  const month = viewDate.month;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const startDay = new Date(year, month, 1).getDay();

  const weeks: (number | null)[][] = [];
  let week: (number | null)[] = [];
  for (let i = 0; i < startDay; i++) week.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    week.push(d);
    if (week.length === 7) {
      weeks.push(week);
      week = [];
    }
  }
  if (week.length) {
    while (week.length < 7) week.push(null);
    weeks.push(week);
  }

  const minDateObj = min ? new Date(min) : null;

  const isDisabled = (day: number) => {
    if (!minDateObj) return false;
    const candidate = new Date(year, month, day);
    return candidate < minDateObj;
  };

  const isSelected = (day: number) => {
    if (!value) return false;
    const [vy, vm, vd] = value.split("-").map(Number);
    return vy === year && vm - 1 === month && vd === day;
  };

  return (
    <div className="datepicker" ref={containerRef} style={{ position: "relative", display: "inline-block" }}>
      <div style={{ display: "flex" }}>
        <input
          type="text"
          placeholder="dd/mm/aaaa"
          value={display}
          onChange={handleInput}
          onClick={() => setOpen(!open)}
          style={{ flex: 1, padding: 8, border: "1px solid #ccc", borderRadius: "4px 0 0 4px" }}
        />
        <button
          type="button"
          onClick={() => setOpen(!open)}
          style={{ padding: 8, border: "1px solid #ccc", borderLeft: "none", borderRadius: "0 4px 4px 0", background: "#f8fafc" }}
        >
          📅
        </button>
      </div>
      {open && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: 0,
            zIndex: 1000,
            background: "white",
            border: "1px solid #e2e8f0",
            borderRadius: 8,
            padding: 16,
            marginTop: 4,
            boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <button type="button" onClick={() => changeMonth(-1)}>‹</button>
            <span style={{ fontWeight: "bold" }}>{monthNames[month]} {year}</span>
            <button type="button" onClick={() => changeMonth(1)}>›</button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 2, textAlign: "center" }}>
            {["D", "L", "M", "X", "J", "V", "S"].map((d) => (
              <div key={d} style={{ fontSize: 12, fontWeight: "bold", color: "#64748b" }}>{d}</div>
            ))}
            {weeks.map((week, i) =>
              week.map((day, j) => (
                <div
                  key={`${i}-${j}`}
                  style={{
                    width: 28,
                    height: 28,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    borderRadius: 4,
                    cursor: day && !isDisabled(day) ? "pointer" : "default",
                    background: day && isSelected(day) ? "#3b82f6" : undefined,
                    color: day && isSelected(day) ? "white" : undefined,
                    opacity: day && isDisabled(day) ? 0.3 : 1,
                  }}
                  onClick={() => day && !isDisabled(day) && handleSelectDay(day)}
                >
                  {day}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
