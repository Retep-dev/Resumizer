import { useEffect, useState } from 'react';

function query(q) {
  return typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(q) : null;
}

/** True when the visitor has asked the OS for reduced motion. */
export function useReducedMotion() {
  const [reduced, setReduced] = useState(() => !!query('(prefers-reduced-motion: reduce)')?.matches);
  useEffect(() => {
    const mq = query('(prefers-reduced-motion: reduce)');
    if (!mq) return undefined;
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);
  return reduced;
}

/** True on devices with a precise pointer (mouse / trackpad). */
export function useFinePointer() {
  const [fine] = useState(() => !!query('(hover: hover) and (pointer: fine)')?.matches);
  return fine;
}
