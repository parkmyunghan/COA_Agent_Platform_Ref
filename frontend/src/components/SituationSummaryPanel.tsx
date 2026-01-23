import React from 'react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { parseThreatLevel } from '../lib/threat-level-parser';

interface SituationSummaryPanelProps {
    situation: any;
}

export const SituationSummaryPanel: React.FC<SituationSummaryPanelProps> = ({ situation }) => {
    if (!situation) {
        return (
            <div className="p-4 bg-gray-50 dark:bg-zinc-800 rounded-lg text-sm text-gray-500 dark:text-gray-400">
                상황 정보가 없습니다.
            </div>
        );
    }

    const approachMode = situation.approach_mode || 'threat_centered';
    const isThreatCentered = approachMode === 'threat_centered';

    return (
        <Card className="border-gray-200 dark:border-zinc-700">
            <CardContent className="p-4 space-y-3">
                <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold text-sm text-gray-900 dark:text-white">상황 요약</h4>
                    <Badge variant={isThreatCentered ? 'destructive' : 'default'}>
                        {isThreatCentered ? '위협 중심' : '임무 중심'}
                    </Badge>
                </div>

                {isThreatCentered ? (
                    <>
                        {/* 위협 중심 요약 */}
                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                                <span className="text-gray-500 dark:text-gray-400">상황 ID:</span>
                                <span className="font-medium text-gray-900 dark:text-white">
                                    {situation.selected_threat_id || situation.위협ID || situation.situation_id || situation.threat_id || 'N/A'}
                                </span>
                            </div>
                            
                            {(() => {
                                // 위협 수준 파싱 (문자열 "HIGH", "MEDIUM", "LOW" 지원)
                                const threatLevelRaw = situation.threat_level || situation.위협수준;
                                const parsed = parseThreatLevel(threatLevelRaw);
                                
                                if (!parsed) {
                                    return null;
                                }
                                
                                const threatLevel = parsed.normalized;
                                const threatLevelPercent = parsed.percent;
                                
                                return (
                                    <div className="flex justify-between">
                                        <span className="text-gray-500 dark:text-gray-400">위협 수준:</span>
                                        <span className={`font-semibold ${
                                            threatLevel >= 0.8 ? 'text-red-600 dark:text-red-400' :
                                            threatLevel >= 0.5 ? 'text-yellow-600 dark:text-yellow-400' :
                                            'text-green-600 dark:text-green-400'
                                        }`}>
                                            {threatLevelPercent}%
                                        </span>
                                    </div>
                                );
                            })()}

                            {(situation.위협유형 || situation.threat_type) && (
                                <div className="flex justify-between">
                                    <span className="text-gray-500 dark:text-gray-400">위협 유형:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">
                                        {situation.위협유형 || situation.threat_type}
                                    </span>
                                </div>
                            )}

                            {(situation.관련축선ID || situation.axis_id) && (
                                <div className="flex justify-between">
                                    <span className="text-gray-500 dark:text-gray-400">관련 축선:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">
                                        {situation.관련축선ID || situation.axis_id}
                                    </span>
                                </div>
                            )}

                            {(situation.발생장소 || situation.location) && (
                                <div className="flex justify-between">
                                    <span className="text-gray-500 dark:text-gray-400">발생 장소:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">
                                        {situation.발생장소 || situation.location}
                                    </span>
                                </div>
                            )}
                        </div>
                    </>
                ) : (
                    <>
                        {/* 임무 중심 요약 */}
                        <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                                <span className="text-gray-500 dark:text-gray-400">임무 ID:</span>
                                <span className="font-medium text-gray-900 dark:text-white">
                                    {situation.mission_id || situation.임무ID || 'N/A'}
                                </span>
                            </div>

                            {(situation.임무명 || situation.mission_name) && (
                                <div className="flex justify-between">
                                    <span className="text-gray-500 dark:text-gray-400">임무명:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">
                                        {situation.임무명 || situation.mission_name}
                                    </span>
                                </div>
                            )}

                            {(situation.임무종류 || situation.mission_type) && (
                                <div className="flex justify-between">
                                    <span className="text-gray-500 dark:text-gray-400">임무 종류:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">
                                        {situation.임무종류 || situation.mission_type}
                                    </span>
                                </div>
                            )}

                            {(situation.관련축선ID || situation.axis_id) && (
                                <div className="flex justify-between">
                                    <span className="text-gray-500 dark:text-gray-400">주요 축선:</span>
                                    <span className="font-medium text-gray-900 dark:text-white">
                                        {situation.관련축선ID || situation.axis_id}
                                    </span>
                                </div>
                            )}
                        </div>
                    </>
                )}

                {/* 공통 정보 */}
                {situation.environment && (
                    <div className="pt-2 border-t border-gray-200 dark:border-zinc-700 space-y-1 text-xs">
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">기상:</span>
                            <span className="text-gray-700 dark:text-gray-300">{situation.environment.weather || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">지형:</span>
                            <span className="text-gray-700 dark:text-gray-300">{situation.environment.terrain || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between">
                            <span className="text-gray-500 dark:text-gray-400">시간:</span>
                            <span className="text-gray-700 dark:text-gray-300">{situation.environment.time_of_day || 'N/A'}</span>
                        </div>
                    </div>
                )}

                {situation.resource_availability !== undefined && (
                    <div className="pt-2 border-t border-gray-200 dark:border-zinc-700">
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-500 dark:text-gray-400">자원 가용성:</span>
                            <span className="font-semibold text-gray-900 dark:text-white">
                                {Math.round(situation.resource_availability * 100)}%
                            </span>
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};
