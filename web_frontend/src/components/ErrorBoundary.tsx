import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

/**
 * Error Boundary to catch React errors and display a fallback UI
 * instead of crashing the entire app
 */
class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
        };
    }

    static getDerivedStateFromError(error: Error): Partial<State> {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('Error Boundary caught an error:', error, errorInfo);
        this.state = {
            hasError: true,
            error,
            errorInfo,
        };
    }

    handleReset = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null,
        });
        window.location.href = '/';
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen bg-sentinel-bg flex items-center justify-center p-4">
                    <div className="max-w-2xl w-full glass-panel rounded-2xl p-8 border border-sentinel-error/20 shadow-neon-red">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="p-3 bg-sentinel-error/10 rounded-full border border-sentinel-error/30">
                                <AlertTriangle className="w-8 h-8 text-sentinel-error" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-white font-heading">
                                    Something went wrong
                                </h1>
                                <p className="text-sentinel-text-muted">
                                    The application encountered an unexpected error
                                </p>
                            </div>
                        </div>

                        {this.state.error && (
                            <div className="mb-6 p-4 bg-sentinel-surface/50 rounded-lg border border-white/5">
                                <h2 className="text-sm font-semibold text-sentinel-text-main mb-2">
                                    Error Details:
                                </h2>
                                <p className="text-sm font-mono text-sentinel-error break-all">
                                    {this.state.error.toString()}
                                </p>
                                {import.meta.env.DEV && this.state.errorInfo && (
                                    <details className="mt-4">
                                        <summary className="cursor-pointer text-sm text-sentinel-text-muted hover:text-white transition-colors">
                                            Stack Trace
                                        </summary>
                                        <pre className="mt-2 text-xs text-sentinel-text-muted overflow-auto max-h-64 p-2 bg-black/30 rounded">
                                            {this.state.errorInfo.componentStack}
                                        </pre>
                                    </details>
                                )}
                            </div>
                        )}

                        <div className="flex gap-3">
                            <button
                                onClick={this.handleReset}
                                className="flex-1 px-4 py-2 bg-sentinel-primary/10 hover:bg-sentinel-primary/20 text-sentinel-primary border border-sentinel-primary/50 rounded-lg font-medium transition-all hover:shadow-neon-blue"
                            >
                                Return to Dashboard
                            </button>
                            <button
                                onClick={() => window.location.reload()}
                                className="flex-1 px-4 py-2 bg-sentinel-surface hover:bg-white/5 text-white border border-white/10 rounded-lg font-medium transition-colors"
                            >
                                Reload Page
                            </button>
                        </div>

                        <p className="mt-6 text-sm text-sentinel-text-muted text-center">
                            If this problem persists, please check the browser console for more details
                        </p>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
