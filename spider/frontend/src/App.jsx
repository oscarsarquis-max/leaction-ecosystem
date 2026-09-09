import { useEffect, useState } from "react";
import ConsoleShell from "./console/ConsoleShell.jsx";
import SpiderBankEntry from "./spiderbank/SpiderBankEntry.jsx";
import ExperienceHub from "./hub/ExperienceHub.jsx";
import { resolveSurface } from "./surfaces.js";
import "./spiderbank/spiderbank.css";

const TITLES = {
  hub: "SPIDER · Plataforma Contextual",
  spiderbank: "SPIDERBANK · Banco Contextual",
  console: "SPIDER CONSOLE · Console Operacional",
};

export default function App() {
  const [path, setPath] = useState(() => window.location.pathname);

  useEffect(() => {
    function sync() {
      setPath(window.location.pathname);
    }
    window.addEventListener("popstate", sync);
    return () => window.removeEventListener("popstate", sync);
  }, []);

  const surface = resolveSurface(path);
  if (typeof document !== "undefined") {
    document.documentElement.dataset.surface = surface;
    document.title = TITLES[surface];
  }

  if (surface === "hub") {
    return <ExperienceHub />;
  }
  if (surface === "console") {
    return <ConsoleShell />;
  }
  return <SpiderBankEntry key={`${path}${typeof window !== "undefined" ? window.location.search : ""}`} />;
}
