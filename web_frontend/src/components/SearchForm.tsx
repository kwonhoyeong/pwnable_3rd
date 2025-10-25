import React, { useState } from 'react';
import { useQueryState } from '../store/queryContext';
import '../styles/form.scss';

export const SearchForm: React.FC = () => {
  const { search, loading } = useQueryState();
  const [pkg, setPkg] = useState('');
  const [cve, setCve] = useState('');

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    await search({ package: pkg || undefined, cve_id: cve || undefined });
  };

  return (
    <form className="search-form" onSubmit={handleSubmit}>
      <div className="search-form__group">
        <label htmlFor="package">패키지(Package)</label>
        <input
          id="package"
          type="text"
          value={pkg}
          onChange={(e) => setPkg(e.target.value)}
          placeholder="lodash"
        />
      </div>
      <div className="search-form__group">
        <label htmlFor="cve">CVE ID</label>
        <input
          id="cve"
          type="text"
          value={cve}
          onChange={(e) => setCve(e.target.value)}
          placeholder="CVE-2023-1234"
        />
      </div>
      <button type="submit" disabled={loading}>
        {loading ? '조회 중...' : '검색(Search)'}
      </button>
    </form>
  );
};

