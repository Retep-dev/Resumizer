import React, { useEffect, useRef, useState } from 'react';

/**
 * Site header. Shows the results tabs once an analysis exists.
 * `tabs` items: { id, label, count?, className }
 */
export default function Navbar({ onHome, onStart, onReset, hasResults, busy, tabs = [], activeTab, onTab, showTabs }) {
  const [confirming, setConfirming] = useState(false);
  const confirmRef = useRef(null);
  const tabRefs = useRef({});

  useEffect(() => {
    if (confirming) confirmRef.current?.focus();
  }, [confirming]);

  // Keep the selected tab visible when the tab row scrolls on small screens.
  useEffect(() => {
    tabRefs.current[activeTab]?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  }, [activeTab, showTabs]);

  // Arrow-key navigation between tabs (WAI-ARIA tabs pattern).
  const onTabKey = (e, i) => {
    const dir = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
    if (!dir && e.key !== 'Home' && e.key !== 'End') return;
    e.preventDefault();
    const next = e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : (i + dir + tabs.length) % tabs.length;
    onTab(tabs[next].id);
    tabRefs.current[tabs[next].id]?.focus();
  };

  return (
    <header className={`site-header ${showTabs ? 'has-tabs' : ''}`}>
      <div className="wrap">
        <div className="site-header__bar">
          <a href="#/" className="wordmark" onClick={(e) => { e.preventDefault(); onHome(); }} aria-label="Resumizer home">
            Resumizer<span className="wordmark__dot" aria-hidden="true" />
          </a>
          <div className="site-header__actions">
            {!hasResults && !busy && (
              <>
                <a className="site-header__nav-link" href="#how" onClick={(e) => { e.preventDefault(); onHome('how'); }}>How it works</a>
                <button type="button" className="btn btn--ink btn--sm" onClick={onStart}>Analyze a resume</button>
              </>
            )}
            {hasResults && !confirming && (
              <button type="button" className="btn btn--sm" onClick={() => setConfirming(true)}>New analysis</button>
            )}
            {hasResults && confirming && (
              <div className="confirm-reset" role="group" aria-label="Start a new analysis">
                <span className="confirm-reset__q">Clear these results?</span>
                <button ref={confirmRef} type="button" className="btn btn--pink btn--sm" aria-label="Clear these results" onClick={() => { setConfirming(false); onReset(); }}>Clear results</button>
                <button type="button" className="btn btn--quiet btn--sm" onClick={() => setConfirming(false)}>Keep</button>
              </div>
            )}
          </div>
        </div>
        {showTabs && (
          <div className="tabs" role="tablist" aria-label="Analysis results">
            {tabs.map((t, i) => (
              <button
                key={t.id}
                ref={(el) => { tabRefs.current[t.id] = el; }}
                type="button"
                role="tab"
                id={`tab-${t.id}`}
                aria-controls={`panel-${t.id}`}
                aria-selected={activeTab === t.id}
                tabIndex={activeTab === t.id ? 0 : -1}
                aria-label={t.short ? `${t.label}${t.count != null ? ` (${t.count})` : ''}` : undefined}
                className={`tab ${t.className}`}
                onClick={() => onTab(t.id)}
                onKeyDown={(e) => onTabKey(e, i)}
              >
                {t.short ? <><span className="tab__long">{t.label}</span><span className="tab__short" aria-hidden="true">{t.short}</span></> : t.label}
                {t.count != null && <span className="tab__count">{t.count}</span>}
              </button>
            ))}
          </div>
        )}
      </div>
    </header>
  );
}
