import React from 'react';
import { renderRoutes } from 'react-router-config';
import { Link, useLocation } from 'react-router-dom';

const App = (props: { route: any }) => {
    const location = useLocation();
    return (
        <div>
            <nav>
              <ul>
				<li className={location.pathname === '/' ? 'active' : ''}>
				  <Link to="/">Home</Link>
				</li>
              </ul>
            </nav>
            {/* child routes will be rendered here */}
            {renderRoutes(props.route.routes)}
        </div>
    );
};

export default App;
