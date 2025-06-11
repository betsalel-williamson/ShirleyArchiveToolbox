import { Routes, Route } from 'react-router-dom'
import IndexPage from './routes/IndexPage'
import ValidatePage from './routes/ValidatePage'
import { Layout } from './components/Layout'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<IndexPage />} />
        <Route path="/validate/:id" element={<ValidatePage />} />
      </Routes>
    </Layout>
  )
}

export default App
