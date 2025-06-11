import React from 'react';
type TransformState = { offsetX: number; offsetY: number; rotation: number; scale: number; };
interface ControlsProps {
    transforms: TransformState;
    onTransformChange: (newTransforms: Partial<TransformState>) => void;
    onCommit: () => void; onUndo: () => void; onRedo: () => void; onRevert: () => void;
    canUndo: boolean; canRedo: boolean;
}

export const Controls: React.FC<ControlsProps> = ({
    transforms, onTransformChange, onCommit, onUndo, onRedo, onRevert, canUndo, canRedo
}) => {
    const handleNumChange = (key: keyof TransformState, value: string) => {
        const numValue = parseFloat(value);
        if (!isNaN(numValue)) onTransformChange({ [key]: numValue });
    };
    return (
        <div className="controls">
            <div className="control-group">
                <label>Rotate:</label>
                <input type="range" min="-45" max="45" value={transforms.rotation} step="0.1"
                    onChange={e => onTransformChange({ rotation: parseFloat(e.target.value) })}
                    onMouseUp={onCommit} onTouchEnd={onCommit} />
                <input type="number" value={transforms.rotation.toFixed(1)} step="0.1"
                    onChange={e => handleNumChange('rotation', e.target.value)} onBlur={onCommit}/>°
            </div>
            <div className="control-group">
                <label>Scale:</label>
                <input type="range" min="0.1" max="2.0" value={transforms.scale} step="0.01"
                    onChange={e => onTransformChange({ scale: parseFloat(e.target.value) })}
                    onMouseUp={onCommit} onTouchEnd={onCommit} />
                <input type="number" value={transforms.scale.toFixed(2)} step="0.01"
                    onChange={e => handleNumChange('scale', e.target.value)} onBlur={onCommit} />x
            </div>
            <div className="control-group">
                <label>Translate:</label>
                <input type="number" value={Math.round(transforms.offsetX)} placeholder="X"
                    onChange={e => handleNumChange('offsetX', e.target.value)} onBlur={onCommit} />
                <input type="number" value={Math.round(transforms.offsetY)} placeholder="Y"
                    onChange={e => handleNumChange('offsetY', e.target.value)} onBlur={onCommit} />px
            </div>
            <div className="control-group action-buttons">
                <button onClick={onUndo} className="secondary-btn" disabled={!canUndo}>Undo</button>
                <button onClick={onRedo} className="secondary-btn" disabled={!canRedo}>Redo</button>
                <button onClick={onRevert} className="danger-btn">Revert to Original</button>
            </div>
            <p>Then, click and drag the red boxes to align them.</p>
        </div>
    );
};
