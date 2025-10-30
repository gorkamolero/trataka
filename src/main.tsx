import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./style.css";

createRoot(document.getElementById("root")!).render(<App />);

// Remove loading screen - this code only runs after JS has downloaded and executed
const loadingScreen = document.getElementById("loading-screen");
if (loadingScreen) {
  loadingScreen.style.opacity = "0";
  loadingScreen.style.transition = "opacity 0.3s ease-out";
  setTimeout(() => loadingScreen.remove(), 300);
}
