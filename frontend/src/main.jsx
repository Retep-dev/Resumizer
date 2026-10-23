import React, { Suspense, lazy } from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

// Design previews live on /design-preview/* and are code-split, so the
// production app at every other path is untouched.
const DesignPreview = lazy(() => import('./design-preview/index.jsx'))
const isDesignPreview = window.location.pathname.startsWith('/design-preview')

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {isDesignPreview ? (
      <Suspense fallback={null}>
        <DesignPreview />
      </Suspense>
    ) : (
      <App />
    )}
  </React.StrictMode>,
)
