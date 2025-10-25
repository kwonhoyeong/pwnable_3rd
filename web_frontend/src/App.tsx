import React, { useState } from 'react';
import { QueryProvider } from './store/queryContext';
import { SearchForm } from './components/SearchForm';
import { ResultCards } from './components/ResultCards';
import './styles/layout.scss';

const App: React.FC = () => {
  return (
    <QueryProvider>
      <div className="app-shell">
        <header className="app-shell__header">
          <h1>npm Threat Intelligence Dashboard</h1>
        </header>
        <main className="app-shell__main">
          <SearchForm />
          <ResultCards />
        </main>
      </div>
    </QueryProvider>
  );
};

export default App;

