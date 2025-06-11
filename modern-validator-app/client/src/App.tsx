// client/src/App.tsx
import { Outlet } from 'react-router-dom';
import IndexPage from './routes/IndexPage';
import ValidatePage, { action as validateAction } from './routes/ValidatePage';

// We remove the `loader` prop entirely. Data fetching is now done inside the components.
export const routes = [
  {
    id: 'root',
    path: '/',
    element: <Layout />,
    children: [
      {
        id: 'index',
        index: true,
        element: <IndexPage />,
      },
      {
        id: 'validate',
        path: 'validate/:id',
        action: validateAction, // Actions still work perfectly!
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
