interface BoundingBox {
  x_min: number; y_min: number; x_max: number; y_max: number;
}
interface Word {
  id: string; text: string; bounding_box: BoundingBox;
}
interface Line { words: Word[]; }
interface Data {
  image_dimensions: { width: number; height: number }; lines: Line[]; [key: string]: any;
}
interface FormData {
  json_data: string; offsetX: string; offsetY: string; rotation: string; scale: string; [key: string]: string;
}

export function applyTransformationsToData(formData: any): Data {
  const data: Data = JSON.parse(formData.json_data);
  const offsetX = parseFloat(formData.offsetX || '0');
  const offsetY = parseFloat(formData.offsetY || '0');
  const rotationDeg = parseFloat(formData.rotation || '0');
  const scale = parseFloat(formData.scale || '1.0');
  const isTransformed = offsetX !== 0 || offsetY !== 0 || rotationDeg !== 0 || scale !== 1.0;
  let cosRad = 1, sinRad = 0;
  const cx = (data.image_dimensions?.width || 0) / 2;
  const cy = (data.image_dimensions?.height || 0) / 2;

  if (isTransformed) {
    const rotationRad = (rotationDeg * Math.PI) / 180;
    cosRad = Math.cos(rotationRad);
    sinRad = Math.sin(rotationRad);
  }

  const allWords = new Map<string, Word>();
  data.lines?.forEach(line => {
    line.words?.forEach(word => {
      if (word.id) allWords.set(word.id, word);
    });
  });

  for (const key in formData) {
    if (key.startsWith('text_')) {
      const wordId = key.replace('text_', '');
      const word = allWords.get(wordId);
      if (word) word.text = formData[key];
    }
  }

  if (isTransformed) {
    for (const word of allWords.values()) {
      if (!word.bounding_box) continue;
      const bbox = word.bounding_box;
      const corners = [
        { x: bbox.x_min, y: bbox.y_min }, { x: bbox.x_max, y: bbox.y_min },
        { x: bbox.x_max, y: bbox.y_max }, { x: bbox.x_min, y: bbox.y_max },
      ];
      const transformedCorners = corners.map(({ x, y }) => {
        const xScaled = cx + (x - cx) * scale;
        const yScaled = cy + (y - cy) * scale;
        const xRot = cx + (xScaled - cx) * cosRad - (yScaled - cy) * sinRad;
        const yRot = cy + (xScaled - cx) * sinRad + (yScaled - cy) * cosRad;
        return { x: xRot + offsetX, y: yRot + offsetY };
      });
      word.bounding_box = {
        x_min: Math.round(Math.min(...transformedCorners.map(p => p.x))),
        y_min: Math.round(Math.min(...transformedCorners.map(p => p.y))),
        x_max: Math.round(Math.max(...transformedCorners.map(p => p.x))),
        y_max: Math.round(Math.max(...transformedCorners.map(p => p.y))),
      };
    }
  }
  return data;
}
