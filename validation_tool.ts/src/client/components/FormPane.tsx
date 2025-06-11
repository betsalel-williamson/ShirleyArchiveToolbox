import React from 'react';
import type { Annotation, TextState } from '../../../types/types';

interface FormPaneProps {
  annotations: Annotation[];
  textState: TextState;
  onTextChange: (wordId: string, newText: string) => void;
  autosaveStatus: { message: string, type: string };
  onCommit: () => void;
  onBack: () => void;
  onWordSelect: (wordId: string) => void;
  formContainerRef: React.RefObject<HTMLDivElement>;
}

const FormPane: React.FC<FormPaneProps> = ({ annotations, textState, onTextChange, autosaveStatus, onCommit, onBack, onWordSelect, formContainerRef }) => {
  return (
    <>
      <div className="p-6 border-b border-gray-200">
        <h3 className="text-2xl font-semibold text-gray-800">Word Transcriptions</h3>
        <span id="autosave-status" className={`text-sm mt-1 ${autosaveStatus.type}`}>
          {autosaveStatus.message}
        </span>
      </div>
      <div ref={formContainerRef} className="flex-grow overflow-y-auto p-6">
        <form onSubmit={(e) => { e.preventDefault(); onCommit(); }} className="space-y-4">
          {annotations.map((word) => (
            <div key={word.id} className="form-group">
              <label htmlFor={`text_${word.id}`} className="block text-sm font-medium text-gray-700 mb-1">
                Word {word.display_id}:
              </label>
              <input
                type="text"
                id={`text_${word.id}`}
                name={`text_${word.id}`}
                value={textState[word.id] || ''}
                onChange={(e) => onTextChange(word.id, e.target.value)}
                onFocus={() => onWordSelect(word.id)}
                className="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          ))}
        </form>
      </div>
      <div className="p-6 border-t border-gray-200 bg-gray-50">
        <div className="flex gap-4">
            <button
                type="button"
                onClick={onCommit}
                className="w-full px-4 py-3 font-semibold text-white bg-green-600 rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
            >
                Commit & Next
            </button>
            <button
                type="button"
                onClick={onBack}
                className="w-full px-4 py-3 font-semibold text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400"
            >
                Back to List
            </button>
        </div>
      </div>
    </>
  );
};

export default FormPane;
