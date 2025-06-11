import { createStore, applyMiddleware, Store } from 'redux';
import thunk from 'redux-thunk';
import rootReducer from '../client/reducers';

export default (): Store => {
  const store = createStore(rootReducer, {}, applyMiddleware(thunk));
  return store;
};
