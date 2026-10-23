import { useCallback, useEffect, useState } from 'react';

// Tiny hash router so the browser Back button moves between the landing page,
// the upload form and the results tabs without adding a routing dependency.
// Routes: '' (landing) | 'analyze' | 'results/<tab>'
function read() {
  return window.location.hash.replace(/^#\/?/, '');
}

export function useHashRoute() {
  const [route, setRoute] = useState(read);

  useEffect(() => {
    const onHash = () => setRoute(read());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const navigate = useCallback((next, { replace = false } = {}) => {
    const hash = next ? `#/${next}` : '#/';
    if (replace) window.history.replaceState(null, '', hash);
    else if (window.location.hash !== hash) window.history.pushState(null, '', hash);
    setRoute(next);
  }, []);

  return [route, navigate];
}
