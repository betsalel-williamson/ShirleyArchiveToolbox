import React from 'react';
import { renderToString } from 'react-dom/server';
import { Provider } from 'react-redux';
import { StaticRouter } from 'react-router-dom/server';
import App from '../client/views/App';
import { Store } from 'redux';

export default (pathname: string, store: Store, context: object, template: string) => {
    const content = renderToString(
        <Provider store={store}>
            <StaticRouter location={pathname}>
                <App />
            </StaticRouter>
        </Provider>
    );

    // Replace placeholders in the HTML template
    if (template) {
        return template
            .replace('<!--app-html-->', content)
            .replace('"{{preloadedState}}"', JSON.stringify(store.getState()).replace(/</g, '\\u003c'));
    }
    return 'Error: HTML template not found.';
};
