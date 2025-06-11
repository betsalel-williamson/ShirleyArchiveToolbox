import { useState, useCallback } from 'react';

export const useUndoableState = <T>(initialState: T) => {
  const [history, setHistory] = useState<T[]>([initialState]);
  const [currentIndex, setCurrentIndex] = useState(0);

  const state = history[currentIndex];

  const setState = useCallback((newState: T, fromInitial?: boolean) => {
    if (JSON.stringify(newState) === JSON.stringify(state) && !fromInitial) {
      return;
    }

    if (fromInitial) {
        setHistory([newState]);
        setCurrentIndex(0);
        return;
    }

    const newHistory = history.slice(0, currentIndex + 1);
    newHistory.push(newState);
    setHistory(newHistory);
    setCurrentIndex(newHistory.length - 1);
  }, [history, currentIndex, state]);

  const undo = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1);
    }
  }, [currentIndex]);

  const redo = useCallback(() => {
    if (currentIndex < history.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  }, [currentIndex, history.length]);

  const resetState = useCallback((resetToState: T) => {
    setHistory([resetToState]);
    setCurrentIndex(0);
  }, []);

  const canUndo = currentIndex > 0;
  const canRedo = currentIndex < history.length - 1;

  return [state, setState, undo, redo, resetState, canUndo, canRedo] as const;
};
