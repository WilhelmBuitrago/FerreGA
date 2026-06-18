import React, { Component, ErrorInfo, ReactNode } from "react";

type Props = { children: ReactNode };
type State = { hasError: boolean; error?: Error; errorInfo?: ErrorInfo };

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Error capturado por ErrorBoundary:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: 24,
          background: "#fee2e2",
          color: "#991b1b",
          borderRadius: 8,
          border: "1px solid #fecaca",
          margin: 16
        }}>
          <h2>❌ Algo salió mal</h2>
          <pre style={{ whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
            {this.state.error?.message}
          </pre>
          {this.state.errorInfo && (
            <details style={{ marginTop: 12 }}>
              <summary>Detalles técnicos</summary>
              <pre style={{ fontSize: 12, color: "#7f1d1d" }}>
                {this.state.errorInfo.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }
    return this.props.children;
  }
}
