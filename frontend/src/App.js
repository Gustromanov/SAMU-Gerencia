import { useEffect } from "react";
import "@/App.css";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

function App() {
  useEffect(() => {
    // Todo o sistema SAMU 192 é renderizado pelo Django em /api/.
    // Este frontend React apenas redireciona a raiz para a aplicação.
    const target = `${BACKEND_URL || ""}/api/`;
    window.location.replace(target);
  }, []);

  return (
    <div
      data-testid="samu-redirect"
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
        background: "linear-gradient(135deg, #7F1D1D, #DC2626 55%, #C2410C)",
        color: "white",
        textAlign: "center",
        padding: "2rem",
      }}
    >
      <div>
        <div
          style={{
            width: 72,
            height: 72,
            borderRadius: 20,
            background: "rgba(255,255,255,0.12)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 1.5rem",
            fontSize: 32,
            fontWeight: 800,
          }}
        >
          192
        </div>
        <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 6 }}>
          SAMU 192 · Sistema de estoque
        </h1>
        <p style={{ opacity: 0.85, fontSize: 14 }}>Abrindo o painel operacional…</p>
        <a
          href={`${BACKEND_URL || ""}/api/`}
          style={{
            display: "inline-block",
            marginTop: 20,
            color: "white",
            fontWeight: 600,
            background: "rgba(255,255,255,0.15)",
            padding: "10px 18px",
            borderRadius: 12,
            textDecoration: "none",
          }}
        >
          Acessar agora →
        </a>
      </div>
    </div>
  );
}

export default App;
