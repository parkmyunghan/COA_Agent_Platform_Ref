import React from 'react';

interface SituationBannerProps {
    situation: any;
    situationSummary?: string;
    approachMode?: 'threat_centered' | 'mission_centered';
}

export const SituationBanner: React.FC<SituationBannerProps> = ({ 
    situation, 
    situationSummary,
    approachMode = 'threat_centered'
}) => {
    if (!situation) return null;

    const isMissionCentered = approachMode === 'mission_centered';
    const sitId = situation.situation_id || situation.위협ID || situation.임무ID || 'N/A';
    
    // 위협 수준/임무 성공 가능성 텍스트 변환
    const threatLevel = situation.threat_level || situation.위협수준;
    let levelText = '미상';
    if (threatLevel !== undefined) {
        const level = typeof threatLevel === 'number' ? threatLevel : parseFloat(threatLevel);
        const normalizedLevel = level > 1 ? level / 100 : level;
        
        if (isMissionCentered) {
            // 임무 중심: 역전 (높은 위협 = 낮은 성공 가능성)
            if (normalizedLevel >= 0.8) levelText = '낮음';
            else if (normalizedLevel >= 0.5) levelText = '보통';
            else levelText = '높음';
        } else {
            // 위협 중심: 정상
            if (normalizedLevel >= 0.8) levelText = '높음';
            else if (normalizedLevel >= 0.5) levelText = '중간';
            else levelText = '낮음';
        }
    }

    // 위치 정보 조립
    const locationRegion = situation.발생지역 || situation.location_region || '';
    const locationName = situation.발생지형명 || situation.location_name || situation.발생장소 || situation.location || '';
    const locationId = situation.발생장소 || situation.location_id || '';
    
    let locationDisplay = '';
    if (locationRegion && locationRegion !== 'N/A') {
        locationDisplay = locationRegion;
    }
    if (locationName && locationName !== 'N/A') {
        locationDisplay += (locationDisplay ? ' ' : '') + locationName;
    }
    if (!locationDisplay && locationId && locationId !== 'N/A') {
        locationDisplay = locationId;
    }
    if (!locationDisplay) {
        locationDisplay = '작전 지역';
    }

    // 축선 정보 조립
    const axisId = situation.관련축선ID || situation.axis_id || '';
    const axisName = situation.관련축선명 || situation.axis_name || '';
    let axisDisplay = '';
    if (axisId && axisId !== 'N/A') {
        if (axisName && axisName !== 'N/A') {
            axisDisplay = `${axisName}(${axisId})`;
        } else {
            axisDisplay = axisId;
        }
    }

    // 시간 정보
    const timeStr = situation.time_str || situation.occurrence_time || '';
    const timePrefix = timeStr ? `**${timeStr}** 현재, ` : '';

    // 브리핑 텍스트 생성
    let briefingText = '';
    if (isMissionCentered) {
        const missionName = situation.임무명 || situation.mission_name || '기본 임무';
        const missionId = situation.임무ID || situation.mission_id || 'N/A';
        const missionType = situation.임무종류 || situation.mission_type || '기본';
        
        briefingText = `${timePrefix}**${locationDisplay}** 일대에서 **${missionName}**(${missionId}) ${missionType} 임무가 하달되었습니다. `;
        if (axisDisplay) {
            briefingText += `주요 작전 축선은 **${axisDisplay}** 방향이며, `;
        }
        briefingText += `현재 분석된 **임무 성공 가능성**은 **${levelText}** 수준입니다.`;
    } else {
        const threatType = situation.위협유형 || situation.threat_type || '미상';
        const enemyUnit = situation.enemy_units || situation.적부대 || '';
        const enemyPrefix = enemyUnit && enemyUnit !== '****' ? `**${enemyUnit}**에 의한 ` : '미상의 위협원에 의한 ';
        
        briefingText = `${timePrefix}**${locationDisplay}** 일대에서 ${enemyPrefix}**${threatType}** 위협이 식별되었습니다. `;
        if (axisDisplay) {
            briefingText += `**${axisDisplay}** 방향 위협 수준은 **${levelText}** 상태입니다.`;
        } else {
            briefingText += `위협 수준은 **${levelText}** 상태입니다.`;
        }
    }

    // 상세 내용
    const description = situation.description || situation.상황설명 || '';
    const summaryDesc = situationSummary ? `\n\n**[분석 요약]**\n${situationSummary}` : '';

    const bannerTitle = isMissionCentered 
        ? `📡 ${sitId} 임무 보고`
        : `📡 ${sitId} 정황 보고`;

    return (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-500 dark:border-yellow-600 p-4 rounded-lg mb-4">
            <div className="flex items-center gap-2 mb-2">
                <h3 className="text-lg font-bold text-yellow-900 dark:text-yellow-300">
                    {bannerTitle}
                </h3>
            </div>
            <div className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed mb-2 line-clamp-2">
                {briefingText.split('**').map((part, idx) => {
                    if (idx % 2 === 1) {
                        return <strong key={idx} className="text-yellow-900 dark:text-yellow-300">{part}</strong>;
                    }
                    return <span key={idx}>{part}</span>;
                })}
            </div>
            {(description || summaryDesc) && (
                <div className="mt-3 pt-3 border-t border-yellow-200 dark:border-yellow-800">
                    <div className="text-xs text-gray-600 dark:text-gray-400 max-h-32 overflow-y-auto">
                        <div className="font-semibold mb-1">상세내용:</div>
                        {description && <div className="mb-2">{description}</div>}
                        {summaryDesc && <div className="whitespace-pre-line">{summaryDesc}</div>}
                    </div>
                </div>
            )}
        </div>
    );
};
