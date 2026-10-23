import React, { Suspense, lazy } from 'react';

// Isolated design-preview routes. Loaded only when the URL starts with
// /design-preview, so the production app bundle and behaviour are unchanged.
const Gallery = lazy(() => import('./Gallery'));
const Atelier = lazy(() => import('./a/AtelierApp'));
const Studio = lazy(() => import('./b/StudioApp'));
const Lab = lazy(() => import('./c/LabApp'));

export default function DesignPreview() {
  const path = window.location.pathname.replace(/\/+$/, '');
  let Screen = Gallery;
  if (path.endsWith('/design-preview/a')) Screen = Atelier;
  else if (path.endsWith('/design-preview/b')) Screen = Studio;
  else if (path.endsWith('/design-preview/c')) Screen = Lab;

  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', background: '#fff' }} />}>
      <Screen />
    </Suspense>
  );
}
