/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import type { Channel, ContextualEnvironment, Publisher } from '../api/catalog';

export type CatalogSelection = {
  publisher: Publisher;
  channel: Channel;
  environment: ContextualEnvironment;
};

type CatalogSelectionContextValue = {
  selection: CatalogSelection | null;
  setSelection: (value: CatalogSelection | null) => void;
};

const CatalogSelectionContext = createContext<CatalogSelectionContextValue | null>(null);

export function CatalogSelectionProvider(props: { children: ReactNode }) {
  const [selection, setSelection] = useState<CatalogSelection | null>(null);
  const value = useMemo(() => ({ selection, setSelection }), [selection]);
  return (
    <CatalogSelectionContext.Provider value={value}>
      {props.children}
    </CatalogSelectionContext.Provider>
  );
}

export function useCatalogSelection(): CatalogSelectionContextValue {
  const context = useContext(CatalogSelectionContext);
  if (context == null) {
    throw new Error('catalog selection is missing');
  }
  return context;
}
