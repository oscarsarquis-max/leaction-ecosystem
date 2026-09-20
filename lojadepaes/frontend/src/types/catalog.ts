export type CatalogPhoto = {
  src: string;
  alt: string;
};

export type MassOption = {
  title: string;
  description: string;
  tag: string;
  photo: CatalogPhoto;
};

export type FormOption = {
  title: string;
  description: string;
  photo: CatalogPhoto;
};

export type IngredientOption = {
  name: string;
  description: string;
};

export type Story = {
  kicker: string;
  title: string;
  text: string;
  photo: CatalogPhoto;
  mediaPosition?: "center" | "left";
};

export type Article = {
  kicker: string;
  title: string;
  readingLabel: string;
  paragraphs: string[];
  photo: CatalogPhoto;
};
