import { useEffect, useRef, useState } from "react";
import { useAIStore, type WhisperUsage, type UsageStats } from "../store/ai";
import { useAccountStore } from "../store/accounts";
import { useCategoriesStore } from "../store/categories";
import { notifyError } from "../ui/toast";
import { api } from "../lib/api";

type AIChatModalProps = {
  open: boolean;
  onClose: () => void;
};

// Valores por defecto para mostrar cuando no hay usage
const DEFAULT_CHAT_USAGE: UsageStats = {
  minute_requests: 0,
  day_requests: 0,
  day_tokens: 0,
  rpm_limit: 30,
  rpd_limit: 1000,
  tpd_limit: 100000,
};

const DEFAULT_WHISPER_USAGE: WhisperUsage = {
  minute_requests: 0,
  day_requests: 0,
  hour_seconds: 0,
  day_seconds: 0,
  rpm_limit: 20,
  rpd_limit: 2000,
  ash_limit: 7200,
  asd_limit: 28800,
};

export function AIChatModal({ open, onClose }: AIChatModalProps) {
  const { messages, sendMessage, isLoading, confirmParsed, cancelParsed, reset, whisperUsage, chatUsage, setWhisperUsage, fetchUsage } = useAIStore();
  const [inputText, setInputText] = useState("");
  const [showUsage, setShowUsage] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const conversationRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const recordingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch usage whenever the modal opens
  useEffect(() => {
    if (open) {
      fetchUsage();
    }
  }, [open]);

  const accounts = useAccountStore((state) => state.accounts);
  const categories = useCategoriesStore((state) => state.categories);

  // Auto-scroll al fondo cuando llega un mensaje nuevo
  useEffect(() => {
    if (conversationRef.current) {
      conversationRef.current.scrollTop = conversationRef.current.scrollHeight;
    }
  }, [messages]);

  // Grabación
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        const duration = recordingDuration;
        const formData = new FormData();
        formData.append("audio", audioBlob, "recording.webm");
        formData.append("duration", duration.toString());

        try {
          const response = await api.post<{ text: string; usage: WhisperUsage }>("/ai/transcribe", formData, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          setInputText(prev => prev + (prev ? " " : "") + response.data.text);
          setWhisperUsage(response.data.usage);
        } catch (error: any) {
          notifyError("Transcripción fallida: " + (error?.response?.data?.detail || error.message));
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
      setRecordingDuration(0);
      const startTime = Date.now();
      const interval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        setRecordingDuration(elapsed);
      }, 1000);
      recordingIntervalRef.current = interval;
    } catch (err) {
      notifyError("No se pudo acceder al micrófono");
    }
  };

  const stopRecording = () => {
    const mediaRecorder = mediaRecorderRef.current;
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
      setIsRecording(false);
    }
  };

  const toggleRecording = () => {
    if (isRecording) stopRecording();
    else startRecording();
  };

  // Cleanup
  useEffect(() => {
    return () => {
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current);
    };
  }, []);

  const handleSend = async () => {
    if (!inputText.trim()) return;
    await sendMessage(inputText.trim());
    setInputText("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  if (!open) return null;

  const formatTime = (ts: number) => new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const getAccountName = (accountId: string) => {
    const acc = accounts.find(a => a.id === accountId);
    return acc?.name || accountId;
  };
  const getCategoryName = (codigo: string) => {
    const cat = categories.find(c => c.codigo === codigo);
    return cat?.nombre || codigo;
  };

  // Formato de segundos a HH:MM:SS
  const formatSeconds = (sec: number) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = Math.floor(sec % 60);
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Uso actual (o valores por defecto)
  const currentChatUsage = chatUsage || DEFAULT_CHAT_USAGE;
  const currentWhisperUsage = whisperUsage || DEFAULT_WHISPER_USAGE;

  return (
    <div style={styles.overlay} onClick={handleClose}>
      <div style={styles.modal} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerTitle}>
            <span role="img" aria-label="robot">🤖</span> Asistente IA
          </div>
          <div style={styles.headerActions}>
            <button
              style={styles.iconButton}
              onClick={() => setShowUsage(!showUsage)}
              title={showUsage ? "Ocultar uso" : "Mostrar uso de recursos"}
              aria-label="Toggle usage panel"
            >
              📊
            </button>
            <button
              style={styles.iconButton}
              onClick={handleClose}
              title="Cerrar"
              aria-label="Cerrar chat"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Body: conversation + lateral panel */}
        <div style={styles.bodyContainer}>
          <div style={styles.conversation} ref={conversationRef}>
            {messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  ...styles.messageRow,
                  justifyContent: msg.sender === "user" ? "flex-end" : "flex-start",
                }}
              >
                <div
                  style={{
                    ...styles.bubble,
                    backgroundColor: msg.sender === "user" ? "#dcf8c6" : "#ffffff",
                    borderTopLeftRadius: msg.sender === "user" ? 12 : 4,
                    borderTopRightRadius: msg.sender === "user" ? 4 : 12,
                    border: msg.sender === "bot" ? "1px solid #e0e0e0" : "none",
                    opacity: msg.cancelled ? 0.6 : 1,
                  }}
                >
                  <div style={styles.messageText}>{msg.text}</div>
{msg.sender === "bot" && msg.parsed && !msg.cancelled && (
  <div style={styles.confirmSection}>
    <div style={styles.confirmLabel}>
      {msg.parsed.movement_type === "transferencia"
        ? "¿Registrar esta transferencia?"
        : msg.parsed.movement_type === "credito"
          ? "¿Registrar este crédito?"
          : "¿Registrar este movimiento?"}
    </div>
    <div style={styles.confirmData}>
      {msg.parsed.movement_type === "ingreso" && (
        <>
          <div><strong>Cuenta:</strong> {getAccountName(msg.parsed.movement.account_id)}</div>
          <div><strong>Monto:</strong> ${Number(msg.parsed.movement.amount).toLocaleString()}</div>
          <div><strong>Categoría:</strong> {getCategoryName(msg.parsed.movement.categoria_codigo)}</div>
          {msg.parsed.movement.description && (
            <div><strong>Desc:</strong> {msg.parsed.movement.description}</div>
          )}
        </>
      )}
      {msg.parsed.movement_type === "egreso" && (
        <>
          <div><strong>Cuenta:</strong> {getAccountName(msg.parsed.movement.account_id)}</div>
          <div><strong>Monto:</strong> ${Number(msg.parsed.movement.amount).toLocaleString()}</div>
          <div><strong>Categoría:</strong> {getCategoryName(msg.parsed.movement.categoria_codigo)}</div>
          {msg.parsed.movement.description && (
            <div><strong>Desc:</strong> {msg.parsed.movement.description}</div>
          )}
        </>
      )}
      {msg.parsed.movement_type === "transferencia" && (
        <>
          <div><strong>Origen:</strong> {getAccountName(msg.parsed.movement.source_account_id)}</div>
          <div><strong>Destino:</strong> {getAccountName(msg.parsed.movement.target_account_id)}</div>
          <div><strong>Monto:</strong> ${Number(msg.parsed.movement.amount).toLocaleString()}</div>
          {msg.parsed.movement.description && (
            <div><strong>Desc:</strong> {msg.parsed.movement.description}</div>
          )}
        </>
      )}
      {msg.parsed.movement_type === "credito" && (
        <>
          <div><strong>Tipo:</strong> {msg.parsed.movement.type === "CREDIT_SALE" ? "Crédito por Cobrar (CxC)" : "Crédito por Pagar (CxP)"}</div>
          <div><strong>Monto:</strong> ${Number(msg.parsed.movement.total_amount).toLocaleString()}</div>
          <div><strong>Vencimiento:</strong> {msg.parsed.movement.due_date}</div>
          {msg.parsed.movement.description && (
            <div><strong>Desc:</strong> {msg.parsed.movement.description}</div>
          )}
        </>
      )}
    </div>
    <div style={styles.confirmActions}>
      <button
        style={{ ...styles.button, ...styles.buttonSecondary }}
        onClick={cancelParsed}
      >
        Cancelar
      </button>
      <button
        style={{ ...styles.button, ...styles.buttonPrimary }}
        onClick={confirmParsed}
      >
        ✅ Confirmar
      </button>
    </div>
  </div>
)}
                  {msg.sender === "bot" && msg.cancelled && (
                    <div style={styles.cancelledBadge}>❌ Cancelado</div>
                  )}
                  {msg.error && (
                    <div style={styles.errorBubble}>
                      {msg.text}
                    </div>
                  )}
                  <div style={styles.timestamp}>
                    {formatTime(msg.timestamp)}
                  </div>
                </div>
              </div>
            ))}
            {isLoading && (
              <div style={{ ...styles.messageRow, justifyContent: "flex-start" }}>
                <div style={{ ...styles.bubble, backgroundColor: "#fff", border: "1px solid #e0e0e0" }}>
                  <div style={styles.typingIndicator}>
                    <span></span><span></span><span></span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Panel lateral de uso */}
          {showUsage && (
            <div style={styles.sidePanel}>
              <div style={styles.usagePanel}>
                {/* Uso Groq (Chat) */}
                <div style={styles.usageSection}>
                  <div style={styles.usageHeader}>
                    <strong>Uso de Groq (Chat)</strong>
                    <small>RPM/RPD/TPD</small>
                  </div>
                  <>
                    <div style={styles.usageItem}>
                      <span>RPM: {currentChatUsage.minute_requests} / {currentChatUsage.rpm_limit}</span>
                      <progress value={Math.min(100, (currentChatUsage.minute_requests / currentChatUsage.rpm_limit) * 100)} max="100" style={styles.progress} />
                    </div>
                    <div style={styles.usageItem}>
                      <span>RPD: {currentChatUsage.day_requests} / {currentChatUsage.rpd_limit}</span>
                      <progress value={Math.min(100, (currentChatUsage.day_requests / currentChatUsage.rpd_limit) * 100)} max="100" style={styles.progress} />
                    </div>
                    <div style={styles.usageItem}>
                      <span>TPD: {currentChatUsage.day_tokens.toLocaleString()} / {currentChatUsage.tpd_limit.toLocaleString()}</span>
                      <progress value={Math.min(100, (currentChatUsage.day_tokens / currentChatUsage.tpd_limit) * 100)} max="100" style={styles.progress} />
                    </div>
                  </>
                  <hr style={{ margin: "12px 0", border: "none", borderTop: "1px solid #e0e0e0" }} />
                </div>

                {/* Uso Whisper */}
                <div style={styles.usageSection}>
                  <div style={styles.usageHeader}>
                    <strong>Uso de Whisper</strong>
                    <small>RPM/RPD/AS</small>
                  </div>
                  <>
                    <div style={styles.usageItem}>
                      <span>RPM: {currentWhisperUsage.minute_requests} / {currentWhisperUsage.rpm_limit}</span>
                      <progress value={Math.min(100, (currentWhisperUsage.minute_requests / currentWhisperUsage.rpm_limit) * 100)} max="100" style={styles.progress} />
                    </div>
                    <div style={styles.usageItem}>
                      <span>RPD: {currentWhisperUsage.day_requests} / {currentWhisperUsage.rpd_limit}</span>
                      <progress value={Math.min(100, (currentWhisperUsage.day_requests / currentWhisperUsage.rpd_limit) * 100)} max="100" style={styles.progress} />
                    </div>
                    <div style={styles.usageItem}>
                      <span>AS/h: {formatSeconds(currentWhisperUsage.hour_seconds)} / {formatSeconds(currentWhisperUsage.ash_limit)}</span>
                      <progress value={Math.min(100, (currentWhisperUsage.hour_seconds / currentWhisperUsage.ash_limit) * 100)} max="100" style={styles.progress} />
                    </div>
                    <div style={styles.usageItem}>
                      <span>AS/d: {formatSeconds(currentWhisperUsage.day_seconds)} / {formatSeconds(currentWhisperUsage.asd_limit)}</span>
                      <progress value={Math.min(100, (currentWhisperUsage.day_seconds / currentWhisperUsage.asd_limit) * 100)} max="100" style={styles.progress} />
                    </div>
                  </>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div style={styles.inputArea}>
          <button
            style={{
              ...styles.button,
              ...styles.micButton,
              backgroundColor: isRecording ? "#e53935" : "#128c7e",
            }}
            onClick={toggleRecording}
            disabled={isLoading}
            title={isRecording ? "Detener grabación" : "Grabar audio"}
          >
            {isRecording ? "⏹️" : "🎤"}
          </button>
          <textarea
            style={{ ...styles.textarea, marginLeft: isRecording ? "8px" : "0" }}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isRecording ? "Grabando..." : "Escribe algo como: 'Registra 10000 del banco por venta'"}
            rows={2}
            disabled={isLoading}
          />
          <button
            style={{ ...styles.button, ...styles.sendButton }}
            onClick={handleSend}
            disabled={isLoading || !inputText.trim()}
          >
            ➤
          </button>
        </div>
      </div>
    </div>
  );
}

// Estilos (sin cambios, los mismos de antes)
const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0,0,0,0.5)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 10000,
  },
  modal: {
    width: "460px",
    maxWidth: "95vw",
    height: "650px",
    maxHeight: "90vh",
    backgroundColor: "#fff",
    borderRadius: "16px",
    display: "flex",
    flexDirection: "column",
    boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "12px 16px",
    backgroundColor: "#075e54",
    color: "#fff",
  },
  headerTitle: {
    fontWeight: 600,
    fontSize: "1.1rem",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  headerActions: {
    display: "flex",
    gap: "8px",
  },
  iconButton: {
    background: "rgba(255,255,255,0.2)",
    border: "none",
    borderRadius: "50%",
    width: "32px",
    height: "32px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    fontSize: "1rem",
    color: "#fff",
  },
  bodyContainer: {
    display: "flex",
    flex: 1,
    overflow: "hidden",
    position: "relative",
  },
  conversation: {
    flex: 1,
    overflowY: "auto",
    padding: "12px",
    backgroundColor: "#e5ddd5",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  sidePanel: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    width: "240px",
    backgroundColor: "#f8f9fa",
    borderLeft: "1px solid #e0e0e0",
    padding: "12px",
    overflowY: "auto",
    zIndex: 10,
  },
  usagePanel: {},
  usageSection: {
    marginBottom: "12px",
  },
  usageHeader: {
    marginBottom: "8px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    fontSize: "0.9rem",
  },
  usageItem: {
    display: "flex",
    alignItems: "center",
    margin: "4px 0",
    fontSize: "0.85rem",
    gap: "8px",
  },
  progress: {
    flex: 1,
    height: "8px",
    borderRadius: "4px",
    accentColor: "#075e54",
  },
  messageRow: {
    display: "flex",
    width: "100%",
  },
  bubble: {
    maxWidth: "80%",
    padding: "8px 12px",
    borderRadius: "12px",
    position: "relative",
    boxShadow: "0 1px 1px rgba(0,0,0,0.1)",
  },
  messageText: {
    marginBottom: "4px",
    lineHeight: "1.4",
    whiteSpace: "pre-wrap",
  },
  timestamp: {
    fontSize: "0.7rem",
    color: "#999",
    textAlign: "right",
    marginTop: "4px",
  },
  confirmSection: {
    marginTop: "8px",
    padding: "8px",
    backgroundColor: "rgba(0,0,0,0.03)",
    borderRadius: "8px",
    border: "1px solid #e0e0e0",
  },
  confirmLabel: {
    fontWeight: 600,
    marginBottom: "4px",
    color: "#075e54",
  },
  confirmData: {
    fontSize: "0.9rem",
    marginBottom: "8px",
    div: {
      margin: "2px 0",
    },
  },
  confirmActions: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "6px",
  },
  cancelledBadge: {
    marginTop: "4px",
    padding: "4px 8px",
    backgroundColor: "#ffebee",
    color: "#c62828",
    borderRadius: "4px",
    fontSize: "0.8rem",
    textAlign: "center",
    display: "inline-block",
  },
  errorBubble: {
    marginTop: "4px",
    padding: "6px 10px",
    backgroundColor: "#ffebee",
    color: "#c62828",
    borderRadius: "8px",
    fontSize: "0.9rem",
  },
  inputArea: {
    padding: "12px",
    borderTop: "1px solid #e0e0e0",
    display: "flex",
    gap: "8px",
    backgroundColor: "#f8f9fa",
  },
  textarea: {
    flex: 1,
    resize: "none",
    padding: "10px",
    border: "1px solid #ccc",
    borderRadius: "20px",
    fontSize: "1rem",
    fontFamily: "inherit",
    outline: "none",
  },
  button: {
    padding: "10px 16px",
    border: "none",
    borderRadius: "20px",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: "0.9rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  buttonPrimary: {
    backgroundColor: "#128c7e",
    color: "#fff",
  },
  buttonSecondary: {
    backgroundColor: "#fff",
    color: "#333",
    border: "1px solid #ccc",
  },
  sendButton: {
    alignSelf: "flex-end",
    width: "44px",
    height: "44px",
    borderRadius: "50%",
    backgroundColor: "#128c7e",
    color: "#fff",
    border: "none",
    fontSize: "1.2rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  micButton: {
    alignSelf: "flex-end",
    width: "44px",
    height: "44px",
    borderRadius: "50%",
    border: "none",
    fontSize: "1.2rem",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  typingIndicator: {
    display: "flex",
    gap: "4px",
    alignItems: "center",
    height: "20px",
    span: {
      width: "8px",
      height: "8px",
      borderRadius: "50%",
      backgroundColor: "#b0bec5",
      animation: "pulse 1s infinite alternate",
    },
  },
};

if (typeof document !== "undefined") {
  const style = document.createElement("style");
  style.textContent = `
    @keyframes pulse {
      0% { opacity: 0.4; transform: scale(0.8); }
      100% { opacity: 1; transform: scale(1); }
    }
  `;
  document.head.appendChild(style);
}
