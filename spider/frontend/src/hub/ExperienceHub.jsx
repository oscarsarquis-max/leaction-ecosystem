import { useEffect, useRef, useState } from "react";
import { INFOGRAPHIC_ALT, INFOGRAPHIC_SRC, NAV } from "./content.js";
import ArchitectureChapter from "./chapters/ArchitectureChapter.jsx";
import CapabilityChapter from "./chapters/CapabilityChapter.jsx";
import ClosingChapter from "./chapters/ClosingChapter.jsx";
import ContextModelChapter from "./chapters/ContextModelChapter.jsx";
import ExecutionStoryChapter from "./chapters/ExecutionStoryChapter.jsx";
import GovernanceChapter from "./chapters/GovernanceChapter.jsx";
import HeroChapter from "./chapters/HeroChapter.jsx";
import IntegrationChapter from "./chapters/IntegrationChapter.jsx";
import LiveExperienceChapter from "./chapters/LiveExperienceChapter.jsx";
import ProblemChapter from "./chapters/ProblemChapter.jsx";
import ExperienceFooter from "./ExperienceFooter.jsx";
import ExperienceHeader from "./ExperienceHeader.jsx";
import "./experience-hub.css";

export { INFOGRAPHIC_ALT, INFOGRAPHIC_SRC };

export default function ExperienceHub() {
  const [open, setOpen] = useState(false);
  const [activeId, setActiveId] = useState("proposicao");
  const closeRef = useRef(null);

  useEffect(() => {
    document.documentElement.dataset.surface = "hub";
    return () => {
      delete document.documentElement.dataset.surface;
    };
  }, []);

  useEffect(() => {
    const nodes = NAV.map((item) => document.getElementById(item.id)).filter(Boolean);
    if (!nodes.length || typeof IntersectionObserver !== "function") return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target?.id) setActiveId(visible.target.id);
      },
      { rootMargin: "-20% 0px -55% 0px", threshold: [0.15, 0.4] },
    );
    nodes.forEach((node) => observer.observe(node));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    function onKey(event) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="sx-root" data-testid="experience-hub">
      <ExperienceHeader activeId={activeId} />
      <HeroChapter />
      <ProblemChapter />
      <ContextModelChapter />
      <ExecutionStoryChapter />
      <CapabilityChapter />
      <IntegrationChapter />
      <LiveExperienceChapter />
      <GovernanceChapter />
      <ArchitectureChapter onExpand={() => setOpen(true)} />
      <ClosingChapter />
      {open ? (
        <div className="sx-lightbox" data-testid="hub-lightbox" role="dialog" aria-modal="true" aria-label="Arquitetura Spider">
          <button type="button" className="sx-lightbox-backdrop" aria-label="Fechar" onClick={() => setOpen(false)} />
          <div className="sx-lightbox-panel">
            <button
              ref={closeRef}
              type="button"
              className="sx-btn sx-btn-secondary"
              data-testid="hub-lightbox-close"
              onClick={() => setOpen(false)}
            >
              Fechar
            </button>
            <img src={INFOGRAPHIC_SRC} alt={INFOGRAPHIC_ALT} />
          </div>
        </div>
      ) : null}
      <ExperienceFooter />
    </div>
  );
}
