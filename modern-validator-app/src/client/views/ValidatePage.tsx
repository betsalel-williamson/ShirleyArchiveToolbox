import React, { Component, Fragment, createRef } from 'react';
import { connect } from 'react-redux';
import { Link, RouteComponentProps } from 'react-router-dom';
import { BoundingBox } from '../components/BoundingBox';
import { Controls } from '../components/Controls';
import { getDocumentById } from '../../server/data';
import { DOC_DETAIL_SUCCESS } from '../reducers/documentsReducer';

// --- Types ---
interface Word { id: string; display_id: number; text: string; bounding_box: { x_min: number; y_min: number; x_max: number; y_max: number; }; }
interface CurrentData { image_source: string; image_dimensions: { width: number, height: number }; lines: { words: Word[] }[]; [key: string]: any }
interface DocumentData { id: number; filename: string; imageSource: string; currentData: CurrentData; error?: string; status?: number }

interface MatchParams { id: string; }
interface Props extends RouteComponentProps<MatchParams> {
    documentData?: DocumentData;
    fetchData: (id: string) => void;
}

class ValidatePage extends Component<Props, any> {

    static appSyncRequestFetching(storeAPI: any) {
        const id = storeAPI.path.split('/').pop();
        return [storeAPI.dispatch(getDocumentById(id).then(res => ({ type: DOC_DETAIL_SUCCESS, payload: res, key: `doc_${id}` })))];
    }

    componentDidMount() {
        if (!this.props.documentData) {
            this.props.fetchData(this.props.match.params.id);
        }
    }

    render() {
        const { documentData } = this.props;
        if (!documentData) {
            return <div className="container"><h1>🌀 Loading document...</h1></div>;
        }

        if (documentData.error) {
            return <div className="container"><h1>Error</h1><p>{documentData.error}</p></div>;
        }

        const annotations = documentData.currentData.lines.flatMap(line => line.words) || [];

        return (
            <div className="container validation-container">
                <div className="image-pane">
                    <h2>{documentData.filename}</h2>
                    <div className="image-wrapper">
                        <img src={`/static/images/${documentData.currentData.image_source}`} alt="Base" />
                        <div id="bbox-overlay" style={{ transformOrigin: 'center' }}>
                            {annotations.map(word => <BoundingBox key={word.id} word={word} />)}
                        </div>
                    </div>
                </div>
                <div className="form-pane">
                    <h3>Word Transcriptions</h3>
                    <form>
                        <div className='form-scroll-area'>
                            {annotations.map(word => (
                                <div className="form-group" key={word.id}>
                                    <label htmlFor={`text_${word.id}`}>Word {word.display_id}:</label>
                                    <input id={`text_${word.id}`} name={`text_${word.id}`} defaultValue={word.text} />
                                </div>
                            ))}
                        </div>
                        <div className="buttons">
                            <button type="submit" className="approve-btn">Commit & Next</button>
                        </div>
                    </form>
                    <Link to="/" className="back-link">← Back to List</Link>
                </div>
            </div>
        );
    }
}

const mapStateToProps = (state: any, ownProps: any) => {
    const docId = ownProps.match.params.id;
    return {
        documentData: state.documents.details[`doc_${docId}`],
    };
};

const mapDispatchToProps = {
    fetchData: (id: string) => (dispatch: any) => getDocumentById(id).then(res => dispatch({ type: DOC_DETAIL_SUCCESS, payload: res, key: `doc_${id}` })),
};

export default connect(mapStateToProps, mapDispatchToProps)(ValidatePage);
