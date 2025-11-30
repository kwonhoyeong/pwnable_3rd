import React, { useState } from 'react';
import { useQueryState } from '../store/queryContext';
import { AlertTriangle, Shield, Activity, Bug } from 'lucide-react';

export const ResultCards: React.FC = () => {
  const { results, error } = useQueryState();
  const [activeIndex, setActiveIndex] = useState<number | null>(0);

  if (error) {
    return <div className="result-error">{error}</div>;
  }

  // Calculate metrics from results
  const cveCount = results.length;
  const maxCvss = results.length > 0 ? Math.max(...results.map(r => r.cvss_score || 0)) : 0;
  const maxEpss = results.length > 0 ? Math.max(...results.map(r => r.epss_score || 0)) : 0;

  // Calculate average or max risk score? Let's use max for safety.
  // Assuming risk_score is available on result items. If not, we might need to derive it.
  // Based on previous code, results have risk_level. Let's assume they might have a numeric score too or we map level to score.
  // Actually, the previous code used `data.risk_score` which was dummy.
  // Let's try to find a numeric score in results. If not, map from level.
  const getScoreFromLevel = (level: string) => {
    switch (level) {
      case 'CRITICAL': return 9.0;
      case 'HIGH': return 7.5;
      case 'MEDIUM': return 5.0;
      case 'LOW': return 2.0;
      default: return 0;
    }
  };

  const maxRiskScore = results.length > 0
    ? Math.max(...results.map(r => (r as any).risk_score || getScoreFromLevel(r.risk_level)))
    : 0;

  const getLevelFromScore = (score: number) => {
    if (score >= 9.0) return 'CRITICAL';
    if (score >= 7.0) return 'HIGH';
    if (score >= 4.0) return 'MEDIUM';
    return 'LOW';
  };

  const level = getLevelFromScore(maxRiskScore);

  const riskColor = level === 'CRITICAL' ? 'text-sentinel-error' :
    level === 'HIGH' ? 'text-sentinel-warning' :
      level === 'MEDIUM' ? 'text-sentinel-primary' :
        'text-sentinel-success';


  if (!results.length) {
    return <div className="result-placeholder">검색 결과가 없습니다(No results)</div>;
  }

  const active = activeIndex !== null ? results[activeIndex] : results[0];

  return (
    <div className="result-grid">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {/* Risk Score Card */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group">
          <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity ${riskColor}`}>
            <AlertTriangle className="w-24 h-24" />
          </div>
          <div className="relative z-10">
            <p className="text-sentinel-text-muted text-sm font-medium uppercase tracking-wider mb-2">Risk Score</p>
            <div className="flex items-end gap-3">
              <span className={`text-5xl font-heading font-bold ${riskColor} drop-shadow-neon`}>
                {maxRiskScore.toFixed(1)}
              </span>
              <span className={`text-lg font-bold mb-1 px-2 py-0.5 rounded border ${level === 'CRITICAL' ? 'text-sentinel-error border-sentinel-error bg-sentinel-error/10' :
                level === 'HIGH' ? 'text-sentinel-warning border-sentinel-warning bg-sentinel-warning/10' :
                  level === 'MEDIUM' ? 'text-sentinel-primary border-sentinel-primary bg-sentinel-primary/10' :
                    'text-sentinel-success border-sentinel-success bg-sentinel-success/10'
                }`}>
                {level}
              </span>
            </div>
          </div>
          <div className={`absolute bottom-0 left-0 h-1 w-full ${level === 'CRITICAL' ? 'bg-sentinel-error' :
            level === 'HIGH' ? 'bg-sentinel-warning' :
              level === 'MEDIUM' ? 'bg-sentinel-primary' :
                'bg-sentinel-success'
            }`}></div>
        </div>

        {/* CVSS Score Card */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity text-sentinel-secondary">
            <Shield className="w-24 h-24" />
          </div>
          <div className="relative z-10">
            <p className="text-sentinel-text-muted text-sm font-medium uppercase tracking-wider mb-2">Max CVSS</p>
            <div className="flex items-end gap-2">
              <span className="text-4xl font-heading font-bold text-white">
                {maxCvss.toFixed(1)}
              </span>
              <span className="text-sentinel-text-muted mb-1">/ 10.0</span>
            </div>
          </div>
        </div>

        {/* EPSS Score Card */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity text-sentinel-primary">
            <Activity className="w-24 h-24" />
          </div>
          <div className="relative z-10">
            <p className="text-sentinel-text-muted text-sm font-medium uppercase tracking-wider mb-2">Max EPSS</p>
            <div className="flex items-end gap-2">
              <span className="text-4xl font-heading font-bold text-white">
                {(maxEpss * 100).toFixed(2)}%
              </span>
              <span className="text-sentinel-text-muted mb-1">Prob.</span>
            </div>
          </div>
        </div>

        {/* CVE Count Card */}
        <div className="glass-panel p-6 rounded-2xl relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity text-white">
            <Bug className="w-24 h-24" />
          </div>
          <div className="relative z-10">
            <p className="text-sentinel-text-muted text-sm font-medium uppercase tracking-wider mb-2">Vulnerabilities</p>
            <div className="flex items-end gap-2">
              <span className="text-4xl font-heading font-bold text-white">
                {cveCount}
              </span>
              <span className="text-sentinel-text-muted mb-1">Found</span>
            </div>
          </div>
        </div>
      </div>
      <div className="result-grid__cards">
        {results.map((item, index) => (
          <article
            key={item.cve_id}
            className={`result-card ${index === activeIndex ? 'result-card--active' : ''}`}
            onClick={() => setActiveIndex(index)}
          >
            <h3>{item.cve_id}</h3>
            <p className="result-card__priority">우선순위(Priority): {item.risk_label}</p>
            <p className="result-card__risk">위험도(Risk): {item.risk_level}</p>
            <p className="result-card__epss">
              EPSS:{' '}
              {typeof item.epss_score === 'number' ? item.epss_score.toFixed(2) : '정보 없음'}
            </p>
            <p className="result-card__cvss">
              CVSS:{' '}
              {typeof item.cvss_score === 'number' ? item.cvss_score.toFixed(1) : '정보 없음'}
            </p>
          </article>
        ))}
      </div>
      <div className="result-grid__detail">
        <h2>{active.cve_id}</h2>
        <p className="result-detail__priority">우선순위(Priority): {active.risk_label}</p>
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
