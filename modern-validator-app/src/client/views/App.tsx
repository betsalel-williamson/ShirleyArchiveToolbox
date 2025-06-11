import React from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import IndexPage from './IndexPage';
import ValidatePage from './ValidatePage';

const App = () => {
    return (
        <div>
            <nav>
                <ul>
                    <li>
                        <NavLink to="/" className={({ isActive }) => isActive ? "active" : ""}>Home</NavLink>
                    </li>
                    {/* Other main navigation links can go here */}
                </ul>
            </nav>

            <Routes>
                <Route path="/" element={<IndexPage />} />
                <Route path="/validate/:id" element={<ValidatePage />} />
                {/* <Route path="*" element={<NotFoundPage />} /> */}
            </Routes>
        </div>
    );
};

export default App;
