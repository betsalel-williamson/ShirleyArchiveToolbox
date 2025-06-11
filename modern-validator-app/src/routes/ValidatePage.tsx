import React, { Suspense, useState, useEffect, useRef, useReducer } from 'react';
import { useFetcher, Link, useNavigate, useParams } from 'react-router-dom';
import { BoundingBox } from '../components/BoundingBox';
import { Controls } from '../components/Controls';
import { fetchData } from '../data-wrapper';
import { getDocumentById } from '../data';

// --- Types (remain the same) ---
interface Word { id: string; display_id: number; text: string; bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number; }; }
interface CurrentData { image_source: string; image_dimensions: { width: number, height: number }; lines: { words: Word[] }[]; [key: string]: any }
interface DocumentData { id: number; filename: string; imageSource: string; currentData: CurrentData, error?: string, status?: number }
type TransformState = { offsetX: number; offsetY: number; rotation: number; scale: number; };
type TextState = { [key:string]: string };
type HistoryState = { transforms: TransformState; texts: TextState; };

// --- Main Validator Component (receives data as prop) ---
function Validator({ documentData }: { documentData: DocumentData }) {
    const fetcher = useFetcher();
    const navigate = useNavigate();
    const { id } = useParams<{ id: string }>();

    const getInitialAnnotations = () => documentData?.currentData?.lines.flatMap(line => line.words) || [];

    const [texts, setTexts] = useState<TextState>({});
    const [transforms, setTransforms] = useState<TransformState>({ offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 });
    const [history, dispatchHistory] = useReducer(historyReducer, { past: [], present: { transforms, texts }, future: [] });
    const [status, setStatus] = useState<{ msg: string, type: string }>({ msg: '', type: '' });

    const isDragging = useRef(false);
    const startPos = useRef({ x: 0, y: 0 });
    const overlayRef = useRef<HTMLDivElement>(null);
    const initialDataRef = useRef(documentData.currentData);

    useEffect(() => {
        if (!documentData || !documentData.currentData) return;
        initialDataRef.current = documentData.currentData;
        const newAnnotations = getInitialAnnotations();
        const newTexts = Object.fromEntries(newAnnotations.map(w => [`text_${w.id}`, w.text]));
        const newTransforms = { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 };
        setTexts(newTexts);
        setTransforms(newTransforms);
        dispatchHistory({ type: 'RESET', payload: { transforms: newTransforms, texts: newTexts } });
        setStatus({ msg: '', type: '' });
    }, [documentData]);

    // ... (rest of the effects and handlers are largely the same)
    // ... (omitting for brevity, they are the same as before)
    // --- Handlers from previous version ---
    const autoSaveState = async (baseData?: CurrentData) => {
        setStatus({ msg: 'Saving...', type: 'status-progress' });
        try {
            const res = await fetch(`/api/documents/${id}/autosave`, { method: 'POST', body: createFormData(baseData) });
            if (res.ok) setStatus({ msg: 'Draft Saved ✓', type: 'status-validated' });
            else throw new Error('Save failed');
        } catch (error) { setStatus({ msg: 'Save Failed!', type: 'status-error' }); }
    };

    useEffect(() => {
        if (!documentData) return;
        const handler = setTimeout(() => {
            if (history.past.length > 0) autoSaveState();
        }, 1500);
        return () => clearTimeout(handler);
    }, [history.present, documentData]);

    const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
        e.preventDefault();
        isDragging.current = true;
        startPos.current = { x: e.clientX - transforms.offsetX, y: e.clientY - transforms.offsetY };
        overlayRef.current?.classList.add('dragging');
    };
    const handleMouseMove = (e: MouseEvent) => {
        if (!isDragging.current) return;
        setTransforms(prev => ({ ...prev, offsetX: e.clientX - startPos.current.x, offsetY: e.clientY - startPos.current.y }));
    };
    const handleMouseUp = () => {
        if (!isDragging.current) return;
        isDragging.current = false;
        overlayRef.current?.classList.remove('dragging');
        dispatchHistory({ type: 'SET', payload: { transforms, texts } });
    };
    useEffect(() => {
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [transforms, texts]);
    const handleTextChange = (e: React.ChangeEvent<HTMLInputElement>) => setTexts(prev => ({ ...prev, [e.target.name]: e.target.value }));
    const handleTextBlur = () => dispatchHistory({ type: 'SET', payload: { transforms, texts } });
    const handleTransformChange = (newT: Partial<TransformState>) => setTransforms({ ...transforms, ...newT });
    const handleTransformCommit = () => dispatchHistory({ type: 'SET', payload: { transforms, texts } });
    const createFormData = (baseData?: CurrentData) => {
        const formData = new FormData();
        formData.append('json_data', JSON.stringify(baseData || initialDataRef.current));
        Object.entries(history.present.transforms).forEach(([k, v]) => formData.append(k, String(v)));
        Object.entries(history.present.texts).forEach(([k, v]) => formData.append(k, v));
        return formData;
    };
     const handleRevert = async () => {
        if (!confirm('Revert to original? This will overwrite your current draft.')) return;
        setStatus({ msg: 'Reverting...', type: 'status-progress' });
        try {
            const res = await fetch(`/api/documents/${id}/revert`, { method: 'POST' });
            const { data } = await res.json();
            initialDataRef.current = data;
            const revertedAnnotations = data.lines.flatMap((line: any) => line.words);
            const revertedTexts = Object.fromEntries(revertedAnnotations.map((w: Word) => [`text_${w.id}`, w.text]));
            const revertedTransforms = { offsetX: 0, offsetY: 0, rotation: 0, scale: 1.0 };
            setTexts(revertedTexts);
            setTransforms(revertedTransforms);
            dispatchHistory({ type: 'RESET', payload: { transforms: revertedTransforms, texts: revertedTexts } });
            autoSaveState(data);
        } catch (error) { setStatus({ msg: 'Revert Failed!', type: 'status-error' }); }
    };
     useEffect(() => {
        if (fetcher.state === 'idle' && fetcher.data) {
            const { nextDocumentId } = fetcher.data as any;
            if (nextDocumentId) navigate(`/validate/${nextDocumentId}`);
            else navigate('/');
        }
    }, [fetcher.data, fetcher.state, navigate]);

    // --- RENDER LOGIC ---
    if (documentData.status === 404) {
        return <div className="container"><h2>{documentData.error}</h2><Link to="/">Back to List</Link></div>;
    }

    const annotations = getInitialAnnotations();

    return (
        <div className="container validation-container">
            <div className="image-pane">
                <h2>{documentData.filename}</h2>
                <Controls {...{ transforms, onTransformChange: handleTransformChange, onCommit: handleTransformCommit,
                    onUndo: () => dispatchHistory({ type: 'UNDO' }), onRedo: () => dispatchHistory({ type: 'REDO' }), onRevert: handleRevert,
                    canUndo: history.past.length > 0, canRedo: history.future.length > 0 }} />
                <div className="image-wrapper">
                    <img src={`/static/images/${documentData.currentData.image_source}`} alt="Base" />
                    <div id="bbox-overlay" ref={overlayRef} onMouseDown={handleMouseDown}
                        style={{ transform: `translate(${transforms.offsetX}px, ${transforms.offsetY}px) rotate(${transforms.rotation}deg) scale(${transforms.scale})`, transformOrigin: 'center' }}>
                        {annotations.map(word => <BoundingBox key={word.id} word={word} />)}
                    </div>
                </div>
            </div>
            <div className="form-pane">
                <h3>Word Transcriptions <span id="autosave-status" className={status.type}>{status.msg}</span></h3>
                <fetcher.Form method="post" action={`/validate/${id}?index`} onSubmit={e => { fetcher.submit(createFormData(), { method: 'post', action: `/validate/${id}?index` }); e.preventDefault(); }}>
                    <div className='form-scroll-area'>
                        {annotations.map(word => (
                            <div className="form-group" key={word.id}>
                                <label htmlFor={`text_${word.id}`}>Word {word.display_id}:</label>
                                <input id={`text_${word.id}`} name={`text_${word.id}`} value={texts[`text_${word.id}`] || ''}
                                    onChange={handleTextChange} onBlur={handleTextBlur} />
                            </div>
                        ))}
                    </div>
                    <div className="buttons">
                        <button type="submit" className="approve-btn" disabled={fetcher.state !== 'idle'}>
                            {fetcher.state !== 'idle' ? 'Committing...' : 'Commit & Next'}
                        </button>
                    </div>
                </fetcher.Form>
                <Link to="/" className="back-link">← Back to List</Link>
            </div>
        </div>
    );
}

// --- Page Level Component with Suspense ---
export default function ValidatePage() {
    const { id } = useParams<{ id: string }>();
    if (!id) return <div>Invalid document ID</div>;

    // This is the data fetching boundary
    const documentData = fetchData(`document_${id}`, () => getDocumentById(id)).read();

    return <Validator documentData={documentData} />;
}

// --- Reducer (remains the same) ---
type Action = { type: 'UNDO' } | { type: 'REDO' } | { type: 'SET', payload: HistoryState } | { type: 'RESET', payload: HistoryState };
interface State { past: HistoryState[]; present: HistoryState; future: HistoryState[]; }
function historyReducer(state: State, action: Action): State {
    const { past, present, future } = state;
    switch (action.type) {
        case 'UNDO': {
            if (past.length === 0) return state;
            const previous = past[past.length - 1];
            return { past: past.slice(0, past.length - 1), present: previous, future: [present, ...future] };
        }
        case 'REDO': {
            if (future.length === 0) return state;
            const next = future[0];
            return { past: [...past, present], present: next, future: future.slice(1) };
        }
        case 'SET':
            if (JSON.stringify(action.payload) === JSON.stringify(present)) return state;
            return { past: [...past, present], present: action.payload, future: [] };
        case 'RESET':
            return { past: [], present: action.payload, future: [] };
    }
}
