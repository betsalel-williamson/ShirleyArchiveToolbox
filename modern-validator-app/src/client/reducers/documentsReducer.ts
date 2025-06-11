import { AnyAction } from "redux";

interface State {
    list: any[] | null;
    details: { [key: string]: any };
}

const initialState: State = {
    list: null,
    details: {}
};

export const DOC_LIST_SUCCESS = 'DOC_LIST_SUCCESS';
export const DOC_DETAIL_SUCCESS = 'DOC_DETAIL_SUCCESS';

export default (state = initialState, action: AnyAction): State => {
    switch (action.type) {
        case DOC_LIST_SUCCESS:
            return { ...state, list: action.payload };
        case DOC_DETAIL_SUCCESS:
            return {
                ...state,
                details: {
                    ...state.details,
                    [action.key]: action.payload,
                },
            };
        default:
            return state;
    }
};
