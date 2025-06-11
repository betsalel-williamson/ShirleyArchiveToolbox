import React from 'react';
import type { Annotation } from '../../types/types';

interface BoundingBoxProps {
  word: Annotation;
}

const BoundingBox: React.FC<BoundingBoxProps> = ({ word }) => {
  const { bounding_box: bbox, display_id } = word;

  if (!bbox) return null;

  const style: React.CSSProperties = {
    left: `${bbox.x_min}px`,
    top: `${bbox.y_min}px`,
    width: `${bbox.x_max - bbox.x_min}px`,
    height: `${bbox.y_max - bbox.y_min}px`,
  };

  return (
    <div className="bounding-box" style={style}>
      <span className="box-label">{display_id}</span>
    </div>
  );
};

export default BoundingBox;
