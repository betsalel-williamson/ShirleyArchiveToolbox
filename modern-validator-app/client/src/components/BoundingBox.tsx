import React from 'react';
interface Word { id: string; display_id: number; bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number; } }

export const BoundingBox: React.FC<{ word: Word }> = ({ word }) => {
    const { bounding_box: bbox, display_id } = word;
    return (
        <div
            className="bounding-box"
            style={{
                left: `${bbox.x_min}px`, top: `${bbox.y_min}px`,
                width: `${bbox.x_max - bbox.x_min}px`, height: `${bbox.y_max - bbox.y_min}px`,
            }}
        >
            <span className="box-label">{display_id}</span>
        </div>
    );
};
