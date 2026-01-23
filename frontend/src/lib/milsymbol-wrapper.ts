import L from 'leaflet';
import ms from 'milsymbol';

export interface SymbolOptions {
    sidc: string;
    size?: number;
    uniqueDesignation?: string; // T (Unique Designation)
    higherFormation?: string; // M (Higher Formation)
    additionalInformation?: string; // H (Additional Information)
    colorMode?: 'Light' | 'Dark' | 'Medium'; // Milsymbol supports color modes
}

/**
 * Generates a Leaflet DivIcon from a generic SIDC code using milsymbol.
 */
export const createMilSymbolIcon = (options: SymbolOptions & { selected?: boolean; pulse?: boolean }): L.DivIcon => {
    const {
        sidc,
        size = 30,
        uniqueDesignation,
        higherFormation,
        additionalInformation,
        selected = false,
        pulse = false,
    } = options;

    const sym = new ms.Symbol(sidc, {
        size: size,
        uniqueDesignation: uniqueDesignation,
        higherFormation: higherFormation,
        additionalInformation: additionalInformation,
        outlineWidth: selected ? 4 : 2,
        strokeWidth: selected ? 3 : 2,
    });

    // SVG HTML 생성
    const svgHtml = sym.asSVG();

    // milsymbol의 실제 크기와 앵커 포인트 가져오기
    const baseSize = sym.getSize();
    const anchor = sym.getAnchor(); // SVG 내부의 실제 논리적 중심점 (x, y)

    // iconSize 계산: 모든 마커를 정사각형으로 만들어 중심 정렬을 정확하게 함
    const maxDimension = Math.max(baseSize.width, baseSize.height);
    const iconSize = selected || pulse
        ? [maxDimension + 20, maxDimension + 20]
        : [maxDimension, maxDimension]; // 일반 마커도 정사각형으로

    // iconAnchor를 항상 iconSize의 정확한 중앙으로 설정
    const iconAnchorX = (iconSize[0] as number) / 2;
    const iconAnchorY = (iconSize[1] as number) / 2;

    // SVG 컨테이너 내부에서 심볼의 논리적 중심(anchor)이 컨테이너 중앙(iconAnchor)에 오도록 오프셋 계산
    // anchor.x, anchor.y는 SVG 내부 좌표이므로, 이를 컨테이너 중앙 [iconAnchorX, iconAnchorY]에 맞춤
    const svgOffsetX = iconAnchorX - anchor.x;
    const svgOffsetY = iconAnchorY - anchor.y;

    // 선택된 마커의 경우 외곽 강조 원 추가
    let finalHtml = '';
    const containerWidth = iconSize[0];
    const containerHeight = iconSize[1];

    if (selected || pulse) {
        // 원의 반경은 심볼 크기의 절반 + 작은 여유 공간
        const circleSize = (Math.max(sym.size, sym.size) / 2) + 5;
        const circleHtml = `
            <circle 
                cx="${iconAnchorX}" 
                cy="${iconAnchorY}" 
                r="${circleSize}" 
                fill="none" 
                stroke="${selected ? '#ef4444' : '#3b82f6'}" 
                stroke-width="3" 
                opacity="${pulse ? '0.6' : '0.8'}"
                class="${pulse ? 'threat-pulse' : ''}"
                style="pointer-events: none; transform-origin: ${iconAnchorX}px ${iconAnchorY}px;"
            />
        `;

        finalHtml = `<div style="position: relative; width: ${containerWidth}px; height: ${containerHeight}px; margin: 0; padding: 0; box-sizing: border-box; overflow: visible;">
            <svg width="${containerWidth}" height="${containerHeight}" style="position: absolute; top: 0; left: 0; pointer-events: none;">
                ${circleHtml}
            </svg>
            <div style="position: absolute; left: ${svgOffsetX}px; top: ${svgOffsetY}px; width: ${baseSize.width}px; height: ${baseSize.height}px; margin: 0; padding: 0; display: flex; align-items: flex-start; justify-content: flex-start;">
                ${svgHtml}
            </div>
        </div>`;
    } else {
        finalHtml = `<div style="position: relative; width: ${containerWidth}px; height: ${containerHeight}px; margin: 0; padding: 0; box-sizing: border-box; overflow: visible;">
            <div style="position: absolute; left: ${svgOffsetX}px; top: ${svgOffsetY}px; width: ${baseSize.width}px; height: ${baseSize.height}px; margin: 0; padding: 0; display: flex; align-items: flex-start; justify-content: flex-start;">
                ${svgHtml}
            </div>
        </div>`;
    }

    return L.divIcon({
        className: selected ? 'milsymbol-icon selected-threat' : 'milsymbol-icon',
        html: finalHtml,
        iconSize: iconSize,
        iconAnchor: [iconAnchorX, iconAnchorY],
        // popupAnchor: 심볼의 실제 크기(baseSize)를 기준으로 설정
        // 컨테이너 크기(iconSize)나 선택 효과(padding)에 상관없이 항상 심볼 상단에 위치하도록 함
        // 심볼 중앙에서 높이의 절반만큼 위로 이동 + 약간의 여백(2px)
        popupAnchor: [0, -(baseSize.height / 2 + 2)],
    });
};
