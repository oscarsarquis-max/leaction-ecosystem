export type WeekRecipeBread = {
  name: string;
  slug: string | null;
  href: string | null;
};

export type WeekRecipeListItem = {
  title: string;
  slug: string;
  summary: string;
  href: string;
  image_url: string | null;
};

export type RecipeSearchPage = {
  q: string;
  page: number;
  page_size: number;
  total: number;
  items: WeekRecipeListItem[];
};

export type WeekRecipePublic = {
  title: string;
  slug: string;
  summary: string;
  image_url: string | null;
  image_alt: string;
  image_caption: string;
  image_focus: string;
  prep_time: string | null;
  yield_text: string | null;
  ingredients: string[];
  method_text?: string;
  steps: string[];
  breads: WeekRecipeBread[];
  href: string;
};

export type WeekRecipeAdmin = WeekRecipePublic & {
  id: string;
  editorial_status: string;
  is_featured: boolean;
  featured_image_id: string | null;
  featured_image_alt: string;
  featured_image_caption: string;
  image_focus_x: number;
  image_focus_y: number;
  prep_time_text: string;
  yield_text: string;
  product_ids: string[];
  publish_gaps: string[];
  other_featured_title?: string | null;
};
