import { useEffect } from "react";
import "@/App.css";

function App() {
  useEffect(() => {
    // Redireciona para a home pública (Quadrix)
    window.location.replace("/home.html");
  }, []);

  return (
    <div
      data-testid="redirect-screen"
      style={{
        position: "fixed",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "system-ui, sans-serif",
        color: "#075FAB",
        background: "#f7f9fb",
      }}
    >
      <p data-testid="redirect-text">Carregando…</p>
    </div>
  );
}

export default App;
