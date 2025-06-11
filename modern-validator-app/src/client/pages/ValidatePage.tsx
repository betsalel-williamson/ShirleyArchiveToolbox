import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useUndoableState } from '../hooks/useUndoableState';
import { useDebounce } from '../hooks/useDebounce';
import Controls from '../components/Controls';
import ImagePane from '../components/ImagePane';
import FormPane from '../components/FormPane';
import type { ValidationData, Annotation, TransformationState, TextState } from '../../types/types';

const ValidatePage: React.FC = () => {
    const { json_filename } = useParams<{ json_filename: string }>();
    const navigate = useNavigate();

    const [data, setData] = useState<ValidationData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [autosaveStatus, setAutosaveStatus] = useState({ message: '', type: ''});

    const [
        state,
        setState,
        undo,
        redo,
        resetState,
        canUndo,
        canRedo
    ] = useUndoableState<{ trans: TransformationState, texts: TextState }>({
        trans: { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 },
        texts: {}
    });

    const debouncedState = useDebounce(state, 1000);

    const getInitialState = (initialData: ValidationData) => {
        let wordCounter = 0;
        const annotations: Annotation[] = [];
        const initialTexts: TextState = {};

        initialData.lines.forEach((line, line_idx) => {
            line.words.forEach((word, word_idx) => {
                const wordId = word.id || `${line_idx}_${word_idx}`;
                word.id = wordId; // Ensure ID exists on original data object
                annotations.push({
                    ...word,
                    id: wordId,
                    display_id: wordCounter + 1,
                });
                initialTexts[wordId] = word.text;
                wordCounter++;
            });
        });

        setData({ ...initialData, annotations });
        const initialState = {
            trans: { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 },
            texts: initialTexts
        };
        setState(initialState, true); // Set initial state without adding to history
    };

    // Fetch initial data
    useEffect(() => {
        if (!json_filename) return;
        setLoading(true);
        fetch(`/api/files/${json_filename}`)
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.json();
            })
            .then((initialData: ValidationData) => {
                getInitialState(initialData);
                setError(null);
            })
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, [json_filename]);

    const autoSave = useCallback(async (currentState: { trans: TransformationState, texts: TextState }) => {
        if (!json_filename || !data) return;

        setAutosaveStatus({ message: "Saving...", type: "status-progress" });

        const formData = new FormData();
        formData.append('json_data', JSON.stringify(data));
        Object.entries(currentState.trans).forEach(([key, value]) => formData.append(key, value.toString()));
        Object.entries(currentState.texts).forEach(([key, value]) => formData.append(`text_${key}`, value));

        try {
            const response = await fetch(`/api/autosave/${json_filename}`, {
                method: 'POST',
                body: new URLSearchParams(formData as any),
            });
            if (!response.ok) throw new Error("Autosave failed on server");
            setAutosaveStatus({ message: "Draft Saved ✓", type: "status-validated" });
        } catch (err) {
            setAutosaveStatus({ message: "Save Failed!", type: "status-error" });
            console.error(err);
        }
    }, [json_filename, data]);

    // Autosave on debounced state change
    useEffect(() => {
        if (debouncedState) {
            autoSave(debouncedState);
        }
    }, [debouncedState, autoSave]);


    const handleRevert = async () => {
        if (!json_filename || !window.confirm('Revert to original? This will overwrite your current draft.')) return;

        try {
            setAutosaveStatus({ message: "Reverting...", type: "status-progress" });
            const response = await fetch(`/api/source-data/${json_filename}`);
            if (!response.ok) throw new Error('Failed to fetch source data.');

            const sourceData = await response.json();
            getInitialState(sourceData); // This resets state and data
            // The autosave effect will then trigger with the clean state.
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error during revert.');
        }
    };

    const handleCommit = async () => {
        if (!json_filename || !data) return;

        const formData = new FormData();
        formData.append('json_data', JSON.stringify(data));
        Object.entries(state.trans).forEach(([key, value]) => formData.append(key, value.toString()));
        Object.entries(state.texts).forEach(([key, value]) => formData.append(`text_${key}`, value));

        try {
            const response = await fetch(`/api/commit/${json_filename}`, {
                method: 'POST',
                body: new URLSearchParams(formData as any),
            });
            if (!response.ok) throw new Error("Commit failed on server");
            const result = await response.json();
            if (result.nextFile) {
                navigate(`/validate/${result.nextFile}`);
            } else {
                navigate('/');
            }
        } catch (err) {
            setAutosaveStatus({ message: "Commit Failed!", type: "status-error" });
            console.error(err);
        }
    };


    if (loading) return <div className="p-8 text-xl">Loading...</div>;
    if (error) return <div className="p-8 text-xl text-red-500">Error: {error}</div>;
    if (!data) return <div className="p-8 text-xl">No data found.</div>;

    return (
        <div className="flex h-screen bg-gray-50">
            <div className="flex-grow p-6 overflow-y-auto">
                <Controls
                    state={state}
                    setState={setState}
                    onUndo={undo}
                    onRedo={redo}
                    canUndo={canUndo}
                    canRedo={canRedo}
                    onRevert={handleRevert}
                />
                <ImagePane
                    imageSrc={`/public/images/${data.image_source}`}
                    annotations={data.annotations || []}
                    transformation={state.trans}
                    onTransformationChange={(newTrans) => setState({ ...state, trans: newTrans })}
                />
            </div>
            <div className="w-1/3 max-w-md h-full flex flex-col border-l border-gray-200 bg-white">
                <FormPane
                    annotations={data.annotations || []}
                    textState={state.texts}
                    onTextChange={(wordId, newText) => setState({ ...state, texts: { ...state.texts, [wordId]: newText } })}
                    autosaveStatus={autosaveStatus}
                    onCommit={handleCommit}
                    onBack={() => navigate('/')}
                />
            </div>
        </div>
    );
};

export default ValidatePage;
