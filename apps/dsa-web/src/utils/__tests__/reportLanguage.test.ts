import { describe, expect, it } from 'vitest';

import { getReportText, normalizeReportLanguage } from '../reportLanguage';
import { getSentimentLabel } from '../../types/analysis';

describe('reportLanguage ko support', () => {
  it('Normalizes ko and falls back to zh for unknown', () => {
    expect(normalizeReportLanguage('ko')).toBe('ko');
    expect(normalizeReportLanguage('en')).toBe('en');
    expect(normalizeReportLanguage('fr')).toBe('zh');
    expect(normalizeReportLanguage(undefined)).toBe('zh');
  });

  it('Returns Korean report copy for ko', () => {
    const ko = getReportText('ko');
    expect(ko.keyInsights).toBe('핵심 인사이트');
    expect(ko.actionAdvice).toBe('대응 전략');
    expect(ko.fullReport).toBe('전체 분석 리포트');
  });

  it('Keeps zh/en report copy unchanged', () => {
    expect(getReportText('zh').keyInsights).toBe('KEY INSIGHTS');
    expect(getReportText('en').keyInsights).toBe('KEY INSIGHTS');
  });

  it('Returns Korean sentiment labels by band', () => {
    expect(getSentimentLabel(90, 'ko')).toBe('매우 낙관');
    expect(getSentimentLabel(50, 'ko')).toBe('중립');
    expect(getSentimentLabel(10, 'ko')).toBe('매우 비관');
    expect(getSentimentLabel(90, 'en')).toBe('Very Bullish');
  });
});
