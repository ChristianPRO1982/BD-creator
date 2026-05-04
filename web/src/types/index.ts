export type Comic = {
  id: string;
  user_id: string;
  name: string;
  export_width: number;
  export_height: number;
  export_quality: number;
  created_at: string;
};

export type Page = {
  id: string;
  comic_id: string;
  template_id: number;
  page_number: number;
  status: "draft" | "validated";
  rendered_image_url: string | null;
  artifact_generated_at: string | null;
};

export type Panel = {
  id: string;
  page_id: string;
  slot_id: number;
  reading_order: number;
  image_asset_id: string | null;
  crop_zoom: number;
  crop_offset_x: number;
  crop_offset_y: number;
};

export type TextBlock = {
  id: string;
  panel_id: string;
  content: string;
  x: number;
  y: number;
  width: number;
  height: number;
  font_size: number;
  bubble_style: string;
  text_color: string;
  background_color: string;
  background_opacity: number;
};

export type Asset = {
  id: string;
  comic_id: string;
  user_id: string;
  name: string;
  file_path: string;
  created_at: string;
};

export type Slot = {
  id: number;
  col_start: number;
  row_start: number;
  col_span: number;
  row_span: number;
  geometry_type: string;
};

export type Template = {
  id: number;
  name: string;
  columns: number;
  rows: number;
  slots: Slot[];
};
