import React from "react";
import { Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import ValidatePage from "./pages/ValidatePage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/validate/:json_filename" element={<ValidatePage />} />
    </Routes>
  );
}

export default App;
