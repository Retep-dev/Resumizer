import React, { forwardRef } from 'react';

/** Server or network failure, with the raw server message available on request. */
const ErrorNotice = forwardRef(function ErrorNotice({ error, onRetry, retryLabel = 'Try again' }, ref) {
  return (
    <div ref={ref} tabIndex={-1} className="notice" role="alert" aria-labelledby="server-error-title">
      <span className="notice__mark" aria-hidden="true">!</span>
      <div>
        <h2 id="server-error-title">{error.title}</h2>
        <p>{error.body}</p>
        {onRetry && (
          <div className="notice__row">
            <button type="button" className="btn btn--ink btn--sm" onClick={onRetry}>{retryLabel}</button>
          </div>
        )}
        {error.detail && (
          <details>
            <summary>Technical details</summary>
            <code>{error.detail}</code>
          </details>
        )}
      </div>
    </div>
  );
});

export default ErrorNotice;
