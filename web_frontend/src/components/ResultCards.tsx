import React, { useEffect, useState } from 'react';
import { useQueryState } from '../store/queryContext';
import '../styles/cards.scss';

export const ResultCards: React.FC = () => {
  const { results, error } = useQueryState();
  const [activeIndex, setActiveIndex] = useState<number | null>(0);

  useEffect(() => {
    if (!results.length) {
      setActiveIndex(null);
      return;
    }
    setActiveIndex((prev) => {
      if (prev === null || prev >= results.length) {
        return 0;
      }
      return prev;
    });
  }, [results]);

  if (error) {
    return <div className="result-error">{error}</div>;
  }

  if (!results.length) {
    return <div className="result-placeholder">검색 결과가 없습니다(No results)</div>;
  }

  const active =
    activeIndex !== null && typeof results[activeIndex] !== 'undefined'
      ? results[activeIndex]
      : results[0];

  return (
    <div className="result-grid">
      <div className="result-grid__cards">
        {results.map((item, index) => (
          <article
            key={item.cve_id}
            className={`result-card ${index === activeIndex ? 'result-card--active' : ''}`}
            onClick={() => setActiveIndex(index)}
          >
            <h3>{item.cve_id}</h3>
            <p className="result-card__priority">우선순위(Priority): {item.priority_label}</p>
            <p className="result-card__risk">위험도(Risk): {item.risk_level}</p>
            <p className="result-card__epss">EPSS: {item.epss_score.toFixed(2)}</p>
            {typeof item.cvss_score === 'number' && (
              <p className="result-card__cvss">CVSS: {item.cvss_score.toFixed(1)}</p>
            )}
          </article>
        ))}
      </div>
      <div className="result-grid__detail">
        <h2>{active.cve_id}</h2>
        <p className="result-detail__priority">우선순위(Priority): {active.priority_label}</p>
        <p>{active.analysis_summary}</p>
        <h4>권고 사항(Recommendations)</h4>
        <ul>
          {active.recommendations.map((rec, idx) => (
            <li key={idx}>{rec}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};
