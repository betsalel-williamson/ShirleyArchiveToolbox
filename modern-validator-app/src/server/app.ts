import express from 'express';
import { matchRoutes } from 'react-router-config';
import compression from 'compression';
import fs from 'fs';
import path from 'path';
import cors from 'cors';

import render from './renderer';
import RoutesConfig from '../client/router/RoutesConfig';
import createNewStore from '../store/createStore';
import apiRouter from './api';

const port = process.env.PORT || 3000;
const app = express();

// Middleware
app.use(compression());
app.use(cors({ origin: '*' }));
app.use(express.static('public'));
app.use(express.static('dist'));

// API routes
app.use('/api', apiRouter);
app.use('/static/images', express.static(path.resolve(__dirname, '../../data/images')));


// SSR catch-all
app.get('*', (req, res) => {
    const store = createNewStore();
    const matchedRoutes = matchRoutes(RoutesConfig, req.path);

    const promises = matchedRoutes.map(({ route }) => {
        if (route.component && (route.component as any).appSyncRequestFetching) {
            const storeAPI = { ...store, path: req.path };
            return (route.component as any).appSyncRequestFetching(storeAPI);
        }
        return null;
    }).flat().filter(p => p); // Flatten and remove nulls

    Promise.all(promises).then(() => {
        const indexFile = path.resolve('./public/index.html');
        fs.readFile(indexFile, 'utf8', (err, template) => {
            if (err) {
                console.error('HTML template read error:', err);
                return res.status(500).send('Oops, something went wrong.');
            }
            const context: { notFound?: boolean } = {};
            const content = render(req.path, store, context, template);

            if (context.notFound) {
                res.status(404);
            }
            res.send(content);
        });
    }).catch(e => {
        console.error("Data fetching error:", e);
        res.status(500).send("Error fetching data for SSR.");
    });
});

app.listen(port, () => {
    console.log(`✅ Server is running on port ${port}, access http://localhost:${port}`);
});
