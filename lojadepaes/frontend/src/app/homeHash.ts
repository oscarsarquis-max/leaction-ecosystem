import { goStorefront } from "../shop/checkoutApi";

export const HOME_SECTION_HASHES = ["#inicio", "#paes", "#criacao", "#mural", "#biblioteca"] as const;

export function currentPathname(): string {
  return window.location.pathname.replace(/\/+$/, "") || "/";
}

export function homeSectionHref(hash: (typeof HOME_SECTION_HASHES)[number], path = currentPathname()): string {
  return path === "/" ? hash : `/${hash}`;
}

export function isUnmodifiedPrimaryClick(event: {
  button?: number;
  metaKey?: boolean;
  ctrlKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
}): boolean {
  return (event.button ?? 0) === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
}

export function goStorefrontUnlessModified(
  event: {
    preventDefault: () => void;
    button?: number;
    metaKey?: boolean;
    ctrlKey?: boolean;
    shiftKey?: boolean;
    altKey?: boolean;
  },
  href: string,
): void {
  if (!isUnmodifiedPrimaryClick(event)) {
    return;
  }
  const destPath = (href.split("#")[0] || "/").replace(/\/+$/, "") || "/";
  if (currentPathname() === destPath) {
    return;
  }
  event.preventDefault();
  goStorefront(href.startsWith("/") ? href : `/${href}`);
}

function scrollElementIntoView(el: HTMLElement): void {
  const top = el.getBoundingClientRect().top + window.scrollY - 24;
  const html = document.documentElement;
  const previous = html.style.scrollBehavior;
  html.style.scrollBehavior = "auto";
  window.scrollTo(0, Math.max(0, top));
  html.style.scrollBehavior = previous;
}

export function scrollToLocationHash(): () => void {
  const id = window.location.hash.replace(/^#/, "");
  if (!id) {
    return () => undefined;
  }
  let frame = 0;
  const run = (): boolean => {
    const el = document.getElementById(id);
    if (!el) {
      return false;
    }
    const go = () => scrollElementIntoView(el);
    if (typeof requestAnimationFrame === "function") {
      frame = requestAnimationFrame(() => {
        frame = requestAnimationFrame(go);
      });
    } else {
      go();
    }
    return true;
  };
  if (run()) {
    return () => cancelAnimationFrame(frame);
  }
  const observer = new MutationObserver(() => {
    if (run()) {
      observer.disconnect();
    }
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
  return () => {
    cancelAnimationFrame(frame);
    observer.disconnect();
  };
}
