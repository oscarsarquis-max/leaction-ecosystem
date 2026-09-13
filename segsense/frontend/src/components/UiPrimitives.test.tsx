import { useState } from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import CopyOnceLink from './CopyOnceLink';
import DestructiveConfirmation from './DestructiveConfirmation';
import OpportunityTabs from './OpportunityTabs';

afterEach(() => {
  cleanup();
});

describe('interface components', () => {
  it('moves between opportunity tabs with keyboard', () => {
    function Harness() {
      const [selected, setSelected] = useState<'content' | 'governance' | 'purpose' | 'links'>(
        'content',
      );
      return (
        <OpportunityTabs
          selected={selected}
          onSelect={setSelected}
          panels={{
            content: <p>Painel de conteúdo</p>,
            governance: <p>Painel de governança</p>,
            purpose: <p>Painel de finalidade</p>,
            links: <p>Painel de links</p>,
          }}
        />
      );
    }
    render(<Harness />);
    expect(screen.getByText('Painel de conteúdo')).toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Conteúdo' }), { key: 'ArrowRight' });
    expect(screen.getByText('Painel de governança')).toBeInTheDocument();
    expect(document.getElementById('tab-governance')).toHaveFocus();
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Governança' }), { key: 'End' });
    expect(screen.getByText('Painel de links')).toBeInTheDocument();
    expect(document.getElementById('tab-links')).toHaveFocus();
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Links contextuais' }), { key: 'Home' });
    expect(screen.getByText('Painel de conteúdo')).toBeInTheDocument();
    expect(document.getElementById('tab-content')).toHaveFocus();
  });

  it('closes a destructive dialog from the safe action', () => {
    function Harness() {
      const [open, setOpen] = useState(true);
      return (
        <DestructiveConfirmation
          open={open}
          title="Revogar este link?"
          cancelLabel="Manter link"
          confirmLabel="Revogar definitivamente"
          returnFocusTo={null}
          onCancel={() => {
            setOpen(false);
          }}
          onConfirm={() => {
            setOpen(false);
          }}
        >
          <p>O endereço deixará de funcionar imediatamente.</p>
        </DestructiveConfirmation>
      );
    }
    render(<Harness />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Manter link' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('announces a copied address', async () => {
    const writeText = vi.fn(() => Promise.resolve());
    Object.assign(navigator, { clipboard: { writeText } });
    const onDismiss = vi.fn();
    render(<CopyOnceLink url="http://127.0.0.1:5178/c/example" onDismiss={onDismiss} />);
    fireEvent.click(screen.getByRole('button', { name: 'Copiar endereço' }));
    expect(await screen.findByText('Endereço copiado')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Concluir' }));
    expect(onDismiss).toHaveBeenCalled();
  });

  it('announces a human clipboard failure without claiming success', async () => {
    const writeText = vi.fn(() => Promise.reject(new Error('denied')));
    Object.assign(navigator, { clipboard: { writeText } });
    render(<CopyOnceLink url="http://127.0.0.1:5178/c/example" onDismiss={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Copiar endereço' }));
    expect(
      await screen.findByText(
        'Não foi possível copiar automaticamente. Selecione o endereço e copie manualmente.',
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText('Endereço copiado')).not.toBeInTheDocument();
  });
});

describe('visual tokens', () => {
  it('defines purple lilac white identity without panne beige', () => {
    const css = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), '../styles/tokens.css'),
      'utf8',
    );
    expect(css).toContain('--segsense-purple-500: #6018e8');
    expect(css).toContain('--segsense-purple-700: #1800b0');
    expect(css).toContain('--segsense-lilac-100: #eae3ff');
    expect(css).toContain('--segsense-white: #ffffff');
    expect(css).toContain('--segsense-ink-900: #18151f');
    expect(css).toContain('--segsense-danger-surface: #fde8e6');
    expect(css).toContain('--segsense-warning-surface: #fff4e5');
    expect(css).toContain('--segsense-admin-logo: 4.5rem');
    expect(css).not.toMatch(/#c4b5a0|#6b645c|#142017/i);
  });
});

describe('vite spa fallback', () => {
  it('keeps history fallback for refresh of admin and public routes', () => {
    const config = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), '../../vite.config.ts'),
      'utf8',
    );
    expect(config).toContain("appType: 'spa'");
  });
});
