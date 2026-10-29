type Props = {
  native?: boolean;
};

export function HomeReturn({ native: _native = false }: Props) {
  return (
    <nav className="home-return" aria-label="Retorno ao site">
      <a href="/">Página principal</a>
    </nav>
  );
}
