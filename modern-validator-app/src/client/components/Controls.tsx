import React from 'react';

interface ControlsProps {
  state: any;
  setState: (newState: any) => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  onRevert: () => void;
}

const Controls: React.FC<ControlsProps> = ({ state, setState, onUndo, onRedo, canUndo, canRedo, onRevert }) => {

  const handleTransformChange = (key: string, value: number) => {
    setState({ ...state, trans: { ...state.trans, [key]: value } });
  };

  const { rotation, scale, offsetX, offsetY } = state.trans;

  return (
    <div className="bg-gray-100 p-4 rounded-lg border border-gray-300 mb-6 space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Rotation */}
        <div className="flex items-center space-x-3">
          <label htmlFor="rotate-slider" className="font-medium text-gray-700 w-20">Rotate:</label>
          <input type="range" id="rotate-slider" min="-45" max="45" value={rotation} step="0.1"
            onChange={(e) => handleTransformChange('rotation', parseFloat(e.target.value))}
            className="flex-grow" />
          <input type="number" value={rotation.toFixed(1)} step="0.1"
            onChange={(e) => handleTransformChange('rotation', parseFloat(e.target.value))}
            className="w-24 p-1 border rounded-md text-sm" />
          <span>°</span>
        </div>

        {/* Scale */}
        <div className="flex items-center space-x-3">
          <label htmlFor="scale-slider" className="font-medium text-gray-700 w-20">Scale:</label>
          <input type="range" id="scale-slider" min="0.1" max="2.0" value={scale} step="0.01"
            onChange={(e) => handleTransformChange('scale', parseFloat(e.target.value))}
            className="flex-grow" />
          <input type="number" value={scale.toFixed(2)} step="0.01"
            onChange={(e) => handleTransformChange('scale', parseFloat(e.target.value))}
            className="w-24 p-1 border rounded-md text-sm" />
          <span>x</span>
        </div>

        {/* Translation */}
        <div className="flex items-center space-x-3 col-span-1 md:col-span-2">
          <label className="font-medium text-gray-700 w-20">Translate:</label>
          <input type="number" value={Math.round(offsetX)} placeholder="X" step="1"
            onChange={(e) => handleTransformChange('offsetX', parseFloat(e.target.value))}
            className="w-24 p-1 border rounded-md text-sm" />
          <input type="number" value={Math.round(offsetY)} placeholder="Y" step="1"
            onChange={(e) => handleTransformChange('offsetY', parseFloat(e.target.value))}
            className="w-24 p-1 border rounded-md text-sm" />
          <span>px</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="pt-4 border-t border-gray-300 flex items-center gap-2">
        <button onClick={onUndo} disabled={!canUndo} className="px-4 py-2 text-sm font-semibold text-white bg-gray-500 rounded-md hover:bg-gray-600 disabled:bg-gray-300 disabled:cursor-not-allowed">Undo</button>
        <button onClick={onRedo} disabled={!canRedo} className="px-4 py-2 text-sm font-semibold text-white bg-gray-500 rounded-md hover:bg-gray-600 disabled:bg-gray-300 disabled:cursor-not-allowed">Redo</button>
        <button onClick={onRevert} className="px-4 py-2 text-sm font-semibold text-white bg-red-500 rounded-md hover:bg-red-600">Revert to Original</button>
      </div>
    </div>
  );
};

export default Controls;
