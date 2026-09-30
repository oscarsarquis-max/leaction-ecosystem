const TEXT_KEY = "lojadepaes_week_recipe_unsaved";
const DB_NAME = "lojadepaes-admin";
const STORE = "recipe-files";

export type RecipeDraftFields = {
  title: string;
  summary: string;
  featured_image_alt: string;
  featured_image_caption: string;
  image_focus_x: number;
  image_focus_y: number;
  prep_time_text: string;
  yield_text: string;
  ingredientsText: string;
  methodText: string;
  product_ids: string[];
};

export type RecoveredDraft = {
  recipeId: string | null;
  draft: RecipeDraftFields;
  file: File | null;
  fileName: string | null;
  recoveredText: boolean;
  recoveredFile: boolean;
};

type StoredDraft = {
  recipeId: string | null;
  draft: RecipeDraftFields;
  fileName: string | null;
};

function draftKey(recipeId: string | null): string {
  return recipeId ?? "new";
}

function openDb(): Promise<IDBDatabase | null> {
  if (typeof indexedDB === "undefined") {
    return Promise.resolve(null);
  }
  return new Promise((resolve) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onerror = () => resolve(null);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE)) {
        request.result.createObjectStore(STORE);
      }
    };
    request.onsuccess = () => resolve(request.result);
  });
}

async function putFile(recipeId: string | null, file: File | null): Promise<void> {
  const db = await openDb();
  if (!db) {
    return;
  }
  await new Promise<void>((resolve) => {
    const tx = db.transaction(STORE, "readwrite");
    const store = tx.objectStore(STORE);
    if (file) {
      store.put(file, draftKey(recipeId));
    } else {
      store.delete(draftKey(recipeId));
    }
    tx.oncomplete = () => resolve();
    tx.onerror = () => resolve();
  });
  db.close();
}

async function getFile(recipeId: string | null): Promise<File | null> {
  const db = await openDb();
  if (!db) {
    return null;
  }
  const file = await new Promise<File | null>((resolve) => {
    const tx = db.transaction(STORE, "readonly");
    const request = tx.objectStore(STORE).get(draftKey(recipeId));
    request.onsuccess = () => resolve((request.result as File | undefined) ?? null);
    request.onerror = () => resolve(null);
  });
  db.close();
  return file;
}

export function persistRecipeDraft(recipeId: string | null, draft: RecipeDraftFields, file: File | null): void {
  const payload: StoredDraft = {
    recipeId,
    draft,
    fileName: file?.name ?? null,
  };
  sessionStorage.setItem(TEXT_KEY, JSON.stringify(payload));
  void putFile(recipeId, file);
}

export async function recoverRecipeDraft(recipeId: string | null): Promise<RecoveredDraft | null> {
  const raw = sessionStorage.getItem(TEXT_KEY);
  if (!raw) {
    return null;
  }
  try {
    const stored = JSON.parse(raw) as StoredDraft;
    if ((stored.recipeId ?? null) !== (recipeId ?? null) || !stored.draft) {
      return null;
    }
    const file = await getFile(recipeId);
    return {
      recipeId: stored.recipeId,
      draft: stored.draft,
      file,
      fileName: stored.fileName,
      recoveredText: true,
      recoveredFile: Boolean(file),
    };
  } catch {
    return null;
  }
}

export function clearRecipeDraft(): void {
  sessionStorage.removeItem(TEXT_KEY);
  void putFile("new", null);
}

export function recoveryMessage(recovered: RecoveredDraft): string {
  if (recovered.recoveredFile) {
    return "Recuperamos o texto e a foto ainda não enviada desta sessão.";
  }
  if (recovered.fileName) {
    return `Recuperamos o texto desta sessão. A foto “${recovered.fileName}” não estava gravada; escolha o arquivo de novo.`;
  }
  return "Recuperamos o texto ainda não salvo desta sessão.";
}
