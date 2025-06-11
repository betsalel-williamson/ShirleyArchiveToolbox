import React from 'react';
import ReactDOM from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { routes } from './App';
import './main.css';

const router = createBrowserRouter(routes);

ReactDOM.hydrateRoot(
  document.getElementById('root')!,
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
