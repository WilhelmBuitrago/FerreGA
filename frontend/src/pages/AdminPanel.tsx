import { useEffect, useState, useMemo } from "react";
import { api, parseApiError } from "../lib/api";
import { notifyError, notifySuccess } from "../ui/toast";

type TableRow = Record<string, any>;

export function AdminPanel() {
  const [password, setPassword] = useState("");
  const [authenticated, setAuthenticated] = useState(false);
  const [tables, setTables] = useState<string[]>([]);
  const [selectedTable, setSelectedTable] = useState<string>("");
  const [rows, setRows] = useState<TableRow[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [skip, setSkip] = useState(0);
  const limit = 50;
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [editingRow, setEditingRow] = useState<TableRow | null>(null);
  const [editForm, setEditForm] = useState<TableRow>({});
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Autenticación
  const handleLogin = async () => {
    setErrorMsg(null);
    try {
      await api.get("/admin/tables", {
        headers: { "X-Admin-Password": password }
      });
      setAuthenticated(true);
      loadTables();
    } catch (e: any) {
      const msg = parseApiError(e) || e.message || "Error de autenticación";
      setErrorMsg(msg);
      notifyError("Contraseña inválida o error de conexión");
    }
  };

  async function loadTables() {
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.get("/admin/tables", {
        headers: { "X-Admin-Password": password }
      });
      const data = res.data;
      let tablitas: string[] = [];
      if (Array.isArray(data)) {
        tablitas = data;
      } else if (data && Array.isArray(data.tables)) {
        tablitas = data.tables;
      } else {
        tablitas = [];
      }
      setTables(tablitas);
      if (tablitas.length > 0 && !selectedTable) {
        setSelectedTable(tablitas[0]);
      } else if (tablitas.length === 0) {
        setSelectedTable("");
      }
    } catch (e: any) {
      const msg = parseApiError(e) || e.message || "Error cargando tablas";
      setErrorMsg(msg);
      notifyError("No se pudieron cargar las tablas");
      setTables([]);
      setSelectedTable("");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (selectedTable) {
      loadRows();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTable, filters, skip]);

  async function loadRows() {
    if (!selectedTable) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const payload = { filters, skip, limit };
      const res = await api.post(`/admin/table/${selectedTable}/rows`, payload, {
        headers: { "X-Admin-Password": password }
      });
      const data = res.data;
      setRows(data.rows);
      setColumns(data.columns);
      setTotal(data.total);
    } catch (e: any) {
      const msg = parseApiError(e) || e.message || "Error cargando registros";
      setErrorMsg(msg);
      notifyError("No se pudieron cargar los registros");
    } finally {
      setLoading(false);
    }
  }

  const handleFilterChange = (col: string, val: string) => {
    setFilters(prev => ({ ...prev, [col]: val }));
    setSkip(0);
  };
  const clearFilters = () => {
    setFilters({});
    setSkip(0);
  };

  const openCreate = () => {
    setEditingRow({});
    setEditForm({});
  };
  const openEdit = (row: TableRow) => {
    setEditingRow(row);
    setEditForm({ ...row });
  };

  const handleEditChange = (col: string, value: any) => {
    setEditForm({ ...editForm, [col]: value });
  };

  const handleSave = async () => {
    try {
      if (editForm.id) {
        await api.patch(`/admin/table/${selectedTable}/${editForm.id}`, editForm, {
          headers: { "X-Admin-Password": password }
        });
        notifySuccess("Registro actualizado");
      } else {
        await api.post(`/admin/table/${selectedTable}/row`, editForm, {
          headers: { "X-Admin-Password": password }
        });
        notifySuccess("Registro creado");
      }
      setEditingRow(null);
      loadRows();
    } catch (e) {
      notifyError(parseApiError(e));
    }
  };

  const handleDelete = async (id: any) => {
    if (!window.confirm(`¿Eliminar registro ${id}? Esta acción no se puede deshacer.`)) return;
    try {
      await api.delete(`/admin/table/${selectedTable}/${id}`, {
        headers: { "X-Admin-Password": password }
      });
      notifySuccess("Registro eliminado");
      loadRows();
    } catch (e) {
      notifyError(parseApiError(e));
    }
  };

  const downloadBackup = async () => {
    try {
      const response = await api.get("/admin/backup-db", {
        headers: { "X-Admin-Password": password },
        responseType: "blob"
      });
      const blob = new Blob([response.data], { type: "text/plain" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const filename = `ferrega_backup_${new Date().toISOString().replace(/[:.]/g, "-")}.sql`;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      notifySuccess("Backup descargado");
    } catch (e) {
      notifyError(parseApiError(e));
    }
  };

  if (!authenticated) {
    return (
      <div className="card" style={{ maxWidth: 400, margin: "auto", marginTop: 40, padding: 24 }}>
        <h2>🔐 Acceso Administrativo</h2>
        <input
          type="password"
          placeholder="Contraseña"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          style={{ width: "100%", padding: 8, marginBottom: 12 }}
        />
        <button className="button button-primary" onClick={handleLogin} style={{ width: "100%" }}>
          Ingresar
        </button>
      </div>
    );
  }

  return (
    <section className="card">
      <div className="page-header">
        <h2 className="page-title">Administración</h2>
         <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
           <select
             value={selectedTable}
             onChange={(e) => { setSelectedTable(e.target.value); setSkip(0); }}
             style={{ padding: 8 }}
             disabled={tables.length === 0}
           >
             {tables.length === 0 && <option value="">Sin tablas</option>}
             {tables.map((t) => (
               <option key={t} value={t}>{t}</option>
             ))}
           </select>
           <button className="button button-ghost" onClick={loadTables} disabled={loading} title="Actualizar tablas">
             🔄
           </button>
           <button className="button button-secondary" onClick={downloadBackup} disabled={loading} title="Descargar backup">
             💾 Backup
           </button>
         </div>
      </div>

      {authenticated && errorMsg && (
        <div style={{ background: "#fee2e2", color: "#991b1b", padding: 12, borderRadius: 8, marginBottom: 16 }}>
          {errorMsg}
        </div>
      )}

      {!authenticated ? (
        <div style={{ maxWidth: 400, margin: "auto", marginTop: 40, padding: 24 }}>
          <h3>🔐 Acceso Administrativo</h3>
          <input
            type="password"
            placeholder="Contraseña"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleLogin()}
            style={{ width: "100%", padding: 8, marginBottom: 12 }}
          />
          <button className="button button-primary" onClick={handleLogin} style={{ width: "100%" }}>
            Ingresar
          </button>
        </div>
      ) : (
        <>
          {tables.length === 0 && !loading && (
            <p style={{ textAlign: "center", marginTop: 40, color: "#64748b" }}>
              No hay tablas disponibles. Verifica la conexión y la contraseña.
            </p>
          )}

          {selectedTable && (
            <>
              <div style={{ marginBottom: 16, display: "flex", flexWrap: "wrap", gap: 8 }}>
                {columns.map((col) => (
                  <div key={col} style={{ display: "inline-flex", flexDirection: "column" }}>
                    <label style={{ fontSize: 12, marginBottom: 2, fontWeight: "bold" }}>{col}</label>
                    <input
                      type="text"
                      placeholder={`Filtrar ${col}`}
                      value={filters[col] || ""}
                      onChange={(e) => handleFilterChange(col, e.target.value)}
                      style={{ padding: 6, width: 160, border: "1px solid #cbd5e1", borderRadius: 4 }}
                    />
                  </div>
                ))}
                <button className="button button-ghost" onClick={clearFilters}>Limpiar filtros</button>
              </div>

              <div style={{ maxHeight: 500, overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: 8 }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead style={{ position: "sticky", top: 0, background: "#f1f5f9", zIndex: 1 }}>
                    <tr>
                      {columns.map((col) => (
                        <th key={col} style={{ border: "1px solid #e2e8f0", padding: 8, textAlign: "left", background: "#f1f5f9", fontWeight: 600 }}>
                          {col}
                        </th>
                      ))}
                      <th style={{ border: "1px solid #e2e8f0", padding: 8, background: "#f1f5f9", fontWeight: 600 }}>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <tr
                        key={row.id}
                        style={{ cursor: "pointer" }}
                        onClick={() => openEdit(row)}
                        onMouseEnter={(e) => e.currentTarget.style.background = "#f8fafc"}
                        onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                      >
                        {columns.map((col) => (
                          <td key={col} style={{ border: "1px solid #e2e8f0", padding: 8 }}>
                            {String(row[col] ?? "")}
                          </td>
                        ))}
                        <td style={{ border: "1px solid #e2e8f0", padding: 8 }}>
                          <button
                            className="button button-ghost"
                            onClick={(e) => { e.stopPropagation(); openEdit(row); }}
                          >
                            ✏️
                          </button>
                          <button
                            className="button button-ghost"
                            onClick={(e) => { e.stopPropagation(); handleDelete(row.id); }}
                          >
                            🗑️
                          </button>
                        </td>
                      </tr>
                    ))}
                    {rows.length === 0 && (
                      <tr>
                        <td colSpan={columns.length + 1} style={{ textAlign: "center", padding: 16, color: "#64748b" }}>
                          No hay registros
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: 12 }}>
                <button
                  className="button button-ghost"
                  onClick={() => setSkip(s => s + limit)}
                  disabled={rows.length < limit}
                >
                  Cargar más
                </button>
                <span style={{ marginLeft: 12, color: "#64748b" }}>
                  {total} registros totales, mostrando {skip + 1}-{Math.min(skip + rows.length, total)}
                </span>
              </div>

              <div style={{ marginTop: 8 }}>
                <button className="button button-secondary" onClick={openCreate}>➕ Nuevo registro</button>
              </div>
            </>
          )}
        </>
      )}

      {/* Modal de edición/creación */}
      {editingRow !== null && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={() => setEditingRow(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 600, width: "90%", maxHeight: "90vh", overflowY: "auto" }}>
            <h3>{editingRow && editingRow.id ? "Editar registro" : "Nuevo registro"}</h3>
            <div className="form-grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))", gap: 12 }}>
              {columns.filter(col => col !== "id").map(col => (
                <label key={col} style={{ display: "flex", flexDirection: "column" }}>
                  <span style={{ fontSize: 12, marginBottom: 4, fontWeight: "bold" }}>{col}</span>
                  <input
                    type="text"
                    value={editForm[col] ?? ""}
                    onChange={(e) => handleEditChange(col, e.target.value)}
                    style={{ padding: 8, border: "1px solid #cbd5e1", borderRadius: 4 }}
                  />
                </label>
              ))}
            </div>
            <div className="modal-actions" style={{ marginTop: 24 }}>
              <button className="button button-ghost" onClick={() => setEditingRow(null)}>Cancelar</button>
              <button className="button button-primary" onClick={handleSave}>Guardar</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
