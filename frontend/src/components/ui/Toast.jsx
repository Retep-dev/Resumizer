import React, { createContext, useCallback, useContext, useRef, useState } from 'react';

const ToastContext = createContext(() => {});

/** Single polite status toast, used for "Copied" style confirmations. */
export function ToastProvider({ children }) {
  const [message, setMessage] = useState('');
  const timer = useRef(null);
  const show = useCallback((text) => {
    setMessage(text);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMessage(''), 2200);
  }, []);
  return (
    <ToastContext.Provider value={show}>
      {children}
      <div role="status" aria-live="polite" className="sr-only">{message}</div>
      {message && <div className="toast" aria-hidden="true">{message}</div>}
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}

/** Copies text and confirms with a toast. Falls back to a hidden textarea. */
export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand('copy');
    ta.remove();
    return ok;
  }
}
