import IndexPage from '../views/IndexPage';
import ValidatePage from '../views/ValidatePage';

// This file is ONLY used by the server to identify which data to fetch.
// It is NOT used for client-side routing.
const LegacyRoutes = [
    {
      path: "/",
      component: IndexPage,
      exact: true
    },
    {
      path: "/validate/:id",
      component: ValidatePage,
    }
];
export default LegacyRoutes;
