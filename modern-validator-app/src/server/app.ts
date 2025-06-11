import express from 'express';
import { matchPath } from 'react-router-dom';
import compression from 'compression';
import fs from 'fs';
import path from 'path';
import cors from 'cors';

import render from './renderer';
import createNewStore from '../store/createStore';
import apiRouter from './api';
import RoutesConfig from '../client/router/LegacyRoutes'; // We'll create a temp legacy config for data fetching

const port = process.env.PORT || 3000;
const app = express();

app.use(compression());
app.use(cors({ origin: '*' }));
app.use(express.static('public'));
app.use(express.static('dist'));

app.use('/api', apiRouter);
app.use('/static/images', express.static(path.resolve(__dirname, '../../data/images')));

app.get('*', (req, res) => {
    const store = createNewStore();

    // Find matching routes to trigger data fetching
    const matchedRoute = RoutesConfig.find(route => matchPath(req.path, route));
    const promises = matchedRoute && (matchedRoute.component as any).appSyncRequestFetching
        ? (matchedRoute.component as any).appSyncRequestFetching({ ...store, path: req.path })
        : [];

    Promise.all(promises.filter(Boolean)).then(() => {
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
    console.log(`✅ Server is running on port ${port}`);
});
