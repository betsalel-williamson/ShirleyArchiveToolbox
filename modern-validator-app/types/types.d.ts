export interface BoundingBox {
  x_min: number;
  y_min: number;
  x_max: number;
  y_max: number;
}

export interface Word {
  id?: string; // Optional on initial load, but assigned during processing
  text: string;
  bounding_box: BoundingBox;
}

export interface Annotation extends Word {
  id: string; // Guaranteed to exist after processing
  display_id: number;
}

export interface Line {
  words: Word[];
}

export interface ImageDimensions {
  width: number;
  height: number;
}

export interface ValidationData {
  image_source: string;
  image_dimensions: ImageDimensions;
  lines: Line[];
  validated?: boolean;
}

export interface TransformationState {
  offsetX: number;
  offsetY: number;
  rotation: number;
  scale: number;
}

export interface TextState {
  [wordId: string]: string;
}
