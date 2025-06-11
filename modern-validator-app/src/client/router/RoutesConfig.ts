import App from '../views/App';
import IndexPage from '../views/IndexPage';
import ValidatePage from '../views/ValidatePage';

const RoutesConfig = [
  {
    component: App,
    routes: [
      {
        path: "/",
        component: IndexPage,
        exact: true
      },
      {
        path: "/validate/:id",
        component: ValidatePage,
      },
      // You can add a 404 component here if needed
    ]
  }
];

export default RoutesConfig;
