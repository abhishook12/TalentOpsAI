import React, { Component } from 'react';
import { AlertTriangle, RefreshCw, RotateCcw, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * BombproofErrorBoundary: High-resilience error boundary that isolates component crashes,
 * prevents white-screen cascades, and provides 1-click automated self-healing recovery.
 */
export default class BombproofErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    console.error(`[BombproofErrorBoundary] Caught exception in ${this.props.componentName || 'Component'}:`, error, errorInfo);
    
    // Auto-reload on stale webpack / vite chunk load errors
    if (error?.name === 'ChunkLoadError' || String(error?.message || '').includes('dynamically imported module')) {
      console.warn('[BombproofErrorBoundary] Stale chunk detected, refreshing page...');
      window.location.reload();
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  handleHardRecovery = () => {
    try {
      sessionStorage.clear();
    } catch (e) {
      console.warn('Could not clear sessionStorage:', e);
    }
    this.setState({ hasError: false, error: null, errorInfo: null });
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      const { componentName = 'Component', compact = false } = this.props;
      const errorMessage = this.state.error?.message || 'An unexpected rendering issue occurred.';

      if (compact) {
        return (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center justify-between text-xs text-rose-300 my-2">
            <div className="flex items-center gap-2 min-w-0 pr-2">
              <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
              <span className="truncate">{componentName} paused</span>
            </div>
            <button
              onClick={this.handleReset}
              className="px-2 py-1 rounded bg-rose-500/20 hover:bg-rose-500/30 text-rose-200 text-[11px] font-semibold flex items-center gap-1 transition-colors flex-shrink-0"
            >
              <RotateCcw className="w-3 h-3" /> Retry
            </button>
          </div>
        );
      }

      return (
        <div
          className="p-6 rounded-2xl shadow-xl my-4 text-left"
          style={{ background: 'var(--card-bg, #18181c)', border: '1px solid var(--card-border, rgba(244, 63, 94, 0.3))' }}
        >
          <div className="flex items-start justify-between gap-4 mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400 flex-shrink-0">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold flex items-center gap-2" style={{ color: 'var(--text-primary, #ffffff)' }}>
                  {componentName} Interrupted
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">
                    Isolated
                  </span>
                </h3>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary, #a1a1aa)' }}>
                  The system isolated this module to prevent the application from crashing.
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={this.handleReset}
                className="px-3 py-1.5 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Self-Heal & Retry
              </button>
              <button
                onClick={this.handleHardRecovery}
                className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors"
                style={{ background: 'var(--panel-bg, #27272a)', color: 'var(--text-primary, #e4e4e7)', border: '1px solid var(--card-border, #3f3f46)' }}
              >
                <RefreshCw className="w-3.5 h-3.5" /> Reset Cache
              </button>
            </div>
          </div>

          <div
            className="p-3 rounded-lg font-mono text-xs text-rose-400 break-all mb-3"
            style={{ background: 'var(--panel-bg, #121214)', border: '1px solid var(--card-border, #27272a)' }}
          >
            {errorMessage}
          </div>

          <div className="pt-3" style={{ borderTop: '1px solid var(--card-border, #27272a)' }}>
            <button
              onClick={() => this.setState(prev => ({ showDetails: !prev.showDetails }))}
              className="text-xs flex items-center gap-1 transition-colors"
              style={{ color: 'var(--text-muted, #71717a)' }}
            >
              {this.state.showDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              {this.state.showDetails ? 'Hide Diagnostics' : 'Show Forensic Diagnostics'}
            </button>

            {this.state.showDetails && (
              <pre
                className="mt-2 p-3 rounded-lg text-[11px] overflow-x-auto max-h-48 custom-scrollbar"
                style={{ background: 'var(--bg-base, #0d0d10)', border: '1px solid var(--card-border, #27272a)', color: 'var(--text-secondary, #a1a1aa)' }}
              >
                {this.state.error?.stack || 'No stack trace available.'}
                {this.state.errorInfo?.componentStack && `\n\nComponent Hierarchy:${this.state.errorInfo.componentStack}`}
              </pre>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
