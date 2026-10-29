import type { AccompanimentCard, AccompanimentStory, AccompanimentsCatalog } from "./accompanimentsApi";

export const ACC_PAGE_SIZE = 12;

export function flattenCatalogItems(catalog: AccompanimentsCatalog): AccompanimentCard[] {
  if (catalog.items?.length) {
    return catalog.items;
  }
  return catalog.stories.flatMap((story) => story.items);
}

export function pageCount(total: number, size = ACC_PAGE_SIZE): number {
  if (total <= 0) {
    return 1;
  }
  return Math.max(1, Math.ceil(total / size));
}

export function clampPage(page: number, total: number, size = ACC_PAGE_SIZE): number {
  const pages = pageCount(total, size);
  if (!Number.isFinite(page) || page < 1) {
    return 1;
  }
  return Math.min(Math.trunc(page), pages);
}

export function slicePage<T>(items: T[], page: number, size = ACC_PAGE_SIZE): T[] {
  const safe = clampPage(page, items.length, size);
  const start = (safe - 1) * size;
  return items.slice(start, start + size);
}

export function groupPageStories(items: AccompanimentCard[]): AccompanimentStory[] {
  const groups: AccompanimentStory[] = [];
  for (const item of items) {
    const occasion = item.occasion || "Sugestões";
    const heading =
      item.story_title && item.story_title.toLowerCase() !== item.name.toLowerCase()
        ? item.story_title
        : occasion;
    const current = groups[groups.length - 1];
    if (!current || current.occasion !== occasion) {
      groups.push({
        occasion,
        title: heading,
        lead: item.story_lead || "",
        items: [item],
      });
    } else {
      current.items.push(item);
    }
  }
  return groups;
}

export function readCatalogPage(): number {
  const raw = Number(new URLSearchParams(window.location.search).get("pagina"));
  return Number.isFinite(raw) ? raw : 1;
}

export function writeCatalogPage(page: number): void {
  const url = new URL(window.location.href);
  if (page <= 1) {
    url.searchParams.delete("pagina");
  } else {
    url.searchParams.set("pagina", String(page));
  }
  window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
}
