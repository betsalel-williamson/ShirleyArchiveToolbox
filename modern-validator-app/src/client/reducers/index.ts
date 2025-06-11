import { combineReducers } from 'redux';
import documentsReducer from './documentsReducer';

export default combineReducers({
    documents: documentsReducer,
});
