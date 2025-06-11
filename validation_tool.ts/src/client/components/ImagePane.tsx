import React, { useRef, useState, useEffect } from 'react';
import type { Annotation, TransformationState } from '../../../types/types';
import BoundingBox from './BoundingBox';

interface ImagePaneProps {
  imageSrc: string;
  annotations: Annotation[];
  transformation: TransformationState;
  onTransformationChange: (newTransformation: TransformationState) => void;
  onWordSelect: (wordId: string) => void;
  imageWrapperRef: React.RefObject<HTMLDivElement>;
}

const ImagePane: React.FC<ImagePaneProps> = ({ imageSrc, annotations, transformation, onTransformationChange, onWordSelect, imageWrapperRef }) => {
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const initialTransform = useRef({ offsetX: 0, offsetY: 0 });

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    setIsDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY };
    initialTransform.current = { offsetX: transformation.offsetX, offsetY: transformation.offsetY };
    e.preventDefault();
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    onTransformationChange({
      ...transformation,
      offsetX: initialTransform.current.offsetX + dx,
      offsetY: initialTransform.current.offsetY + dy,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    const handleMouseUpGlobal = () => setIsDragging(false);
    window.addEventListener('mouseup', handleMouseUpGlobal);
    return () => window.removeEventListener('mouseup', handleMouseUpGlobal);
  }, []);

  return (
    <div className="flex justify-center items-start">
        <div ref={imageWrapperRef} className="image-wrapper" onMouseMove={handleMouseMove} onMouseUp={handleMouseUp} onMouseLeave={handleMouseUp}>
            <img src={imageSrc} alt="Document for validation" />
            <div
                id="bbox-overlay"
                className={isDragging ? 'dragging' : ''}
                style={{
                    transform: `translate(${transformation.offsetX}px, ${transformation.offsetY}px) rotate(${transformation.rotation}deg) scale(${transformation.scale})`,
                }}
                onMouseDown={handleMouseDown}
            >
                {annotations.map((word) => (
                    <BoundingBox key={word.id} word={word} onClick={onWordSelect} />
                ))}
            </div>
        </div>
    </div>
  );
};

export default ImagePane;
