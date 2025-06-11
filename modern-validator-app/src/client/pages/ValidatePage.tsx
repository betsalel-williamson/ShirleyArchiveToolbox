import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useUndoableState } from '../hooks/useUndoableState';
import { useDebounce } from '../hooks/useDebounce';
import Controls from '../components/Controls';
import ImagePane from '../components/ImagePane';
import FormPane from '../components/FormPane';
import type { ValidationData, Annotation, TransformationState, TextState } from '../../../types/types';

const ValidatePage: React.FC = () => {
    const { json_filename } = useParams<{ json_filename: string }>();
    const navigate = useNavigate();

    const formContainerRef = useRef<HTMLDivElement>(null);
    const imageWrapperRef = useRef<HTMLDivElement>(null);

    const [baseData, setBaseData] = useState<ValidationData | null>(null);
    const [annotations, setAnnotations] = useState<Annotation[]>([]);

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

    const initializeStates = (initialData: ValidationData) => {
        let wordCounter = 0;
        const processedAnnotations: Annotation[] = [];
        const initialTexts: TextState = {};

        initialData.lines.forEach((line, line_idx) => {
            line.words.forEach((word, word_idx) => {
                const wordId = word.id || `${line_idx}_${word_idx}`;
                word.id = wordId;

                processedAnnotations.push({
                    ...word,
                    id: wordId,
                    display_id: wordCounter + 1,
                });
                initialTexts[wordId] = word.text;
                wordCounter++;
            });
        });

        setBaseData(initialData);
        setAnnotations(processedAnnotations);

        const initialState = {
            trans: { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 },
            texts: initialTexts
        };
        resetState(initialState);
    };

    useEffect(() => {
        if (!json_filename) return;
        setLoading(true);
        fetch(`/api/files/${json_filename}`)
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.json();
            })
            .then((initialData: ValidationData) => {
                initializeStates(initialData);
                setError(null);
            })
            .catch(err => setError(err.message))
            .finally(() => setLoading(false));
    }, [json_filename, resetState]);

    const autoSave = useCallback(async (currentState: { trans: TransformationState, texts: TextState }) => {
        if (!json_filename || !baseData) return;

        setAutosaveStatus({ message: "Saving...", type: "status-progress" });

        const formData = new URLSearchParams();
        Object.entries(currentState.trans).forEach(([key, value]) => formData.append(key, value.toString()));
        Object.entries(currentState.texts).forEach(([key, value]) => formData.append(`text_${key}`, value));

        try {
            const response = await fetch(`/api/autosave/${json_filename}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData,
            });
            if (!response.ok) throw new Error("Autosave failed on server");
            setAutosaveStatus({ message: "Draft Saved ✓", type: "status-validated" });
        } catch (err) {
            setAutosaveStatus({ message: "Save Failed!", type: "status-error" });
            console.error(err);
        }
    }, [json_filename, baseData]);

    useEffect(() => {
        if (debouncedState && (canUndo || canRedo)) {
            autoSave(debouncedState);
        }
    }, [debouncedState, autoSave, canUndo, canRedo]);

    const handleWordSelect = (wordId: string) => {
        const formEl = formContainerRef.current?.querySelector(`#text_${wordId}`);
        formEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });

        const word = annotations.find(a => a.id === wordId);
        const imageWrapper = imageWrapperRef.current;
        if (!word || !imageWrapper) return;

        const newScale = 1.5;
        const bbox = word.bounding_box;
        const boxCenterX = bbox.x_min + (bbox.x_max - bbox.x_min) / 2;
        const boxCenterY = bbox.y_min + (bbox.y_max - bbox.y_min) / 2;

        const wrapperWidth = imageWrapper.clientWidth;
        const wrapperHeight = imageWrapper.clientHeight;

        const newOffsetX = (wrapperWidth / 2) - (boxCenterX * newScale);
        const newOffsetY = (wrapperHeight / 2) - (boxCenterY * newScale);

        setState({
            ...state,
            trans: {
                ...state.trans,
                scale: newScale,
                offsetX: newOffsetX,
                offsetY: newOffsetY,
            }
        });
    };

    const handleResetView = () => {
        setState({
            ...state,
            trans: { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 }
        })
    };

    const handleRevert = async () => {
        if (!json_filename || !window.confirm('Revert to original? This will overwrite your current draft.')) return;

        try {
            setAutosaveStatus({ message: "Reverting...", type: "status-progress" });
            const response = await fetch(`/api/source-data/${json_filename}`);
            if (!response.ok) throw new Error('Failed to fetch source data.');

            const sourceData = await response.json();
            initializeStates(sourceData);
            const sourceTexts = sourceData.lines.flatMap((l: any) => l.words).reduce((acc: any, w: any) => ({...acc, [w.id]: w.text}), {});
            await autoSave({ trans: { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 }, texts: sourceTexts });
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Unknown error during revert.');
        }
    };

    const handleCommit = async () => {
        if (!json_filename || !baseData) return;

        const formData = new URLSearchParams();
        Object.entries(state.trans).forEach(([key, value]) => formData.append(key, value.toString()));
        Object.entries(state.texts).forEach(([key, value]) => formData.append(`text_${key}`, value));

        try {
            const response = await fetch(`/api/commit/${json_filename}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData,
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
    if (!baseData) return <div className="p-8 text-xl">No data found.</div>;

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
                    onResetView={handleResetView}
                />
                <ImagePane
                    imageWrapperRef={imageWrapperRef}
                    imageSrc={`/images/${baseData.image_source}`}
                    annotations={annotations}
                    transformation={state.trans}
                    onTransformationChange={(newTrans) => setState({ ...state, trans: newTrans })}
                    onWordSelect={handleWordSelect}
                />
            </div>
            <div className="w-1/3 max-w-md h-full flex flex-col border-l border-gray-200 bg-white">
                <FormPane
                    formContainerRef={formContainerRef}
                    annotations={annotations}
                    textState={state.texts}
                    onTextChange={(wordId, newText) => setState({ ...state, texts: { ...state.texts, [wordId]: newText } })}
                    autosaveStatus={autosaveStatus}
                    onCommit={handleCommit}
                    onBack={() => navigate('/')}
                    onWordSelect={handleWordSelect}
                />
            </div>
        </div>
    );
};

export default ValidatePage;
