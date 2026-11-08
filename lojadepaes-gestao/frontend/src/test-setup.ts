import "@testing-library/jest-dom/vitest";

// o jsdom não implementa a rolagem da janela
window.scrollTo = () => {};
