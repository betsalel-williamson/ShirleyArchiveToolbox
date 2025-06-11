import { Outlet } from 'react-router-dom';
import IndexPage, { loader as indexLoader } from './routes/IndexPage';
import ValidatePage, { loader as validateLoader, action as validateAction } from './routes/ValidatePage';

export const routes = [
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        loader: indexLoader,
        element: <IndexPage />,
      },
      {
        path: 'validate/:id',
        loader: validateLoader,
        action: validateAction,
        element: <ValidatePage />,
      }
    ],
  },
];

function Layout() {
  return (
    <div className="app-layout">
      <Outlet />
    </div>
  );
}
