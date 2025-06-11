import React from 'react';
import ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import { BrowserRouter } from 'react-router-dom';
import createNewStore from '../store/createStore';
import App from './views/App';
import './index.scss';

// Grab the initial state from a global variable injected into the server-rendered HTML
const preloadedState = window.__PRELOADED_STATE__;
delete window.__PRELOADED_STATE__;

const store = createNewStore();

ReactDOM.hydrate(
  <Provider store={store}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </Provider>,
  document.querySelector('#app')
);

declare global {
  interface Window {
    __PRELOADED_STATE__?: any;
  }
}
