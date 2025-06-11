import { hydrateRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

// This is the client-side hydration part.
// We are essentially "re-playing" the fetch call on the client,
// but since the data is already in the script tag, our wrapper will
// resolve it instantly without a network call.
if (window.__INITIAL_DATA__) {
  const { key, data } = window.__INITIAL_DATA__;
  const cache = new Map([[key, { read: () => data }]]);
  // You would need a more robust way to share this cache with the app,
  // typically via a React Context, but for this simple case, we can
  // adapt the components to handle it.
}


hydrateRoot(
  document.getElementById('root') as HTMLElement,
  <BrowserRouter>
    <App />
  </BrowserRouter>
)
