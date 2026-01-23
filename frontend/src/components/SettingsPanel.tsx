import React, { useState } from 'react';
import { Checkbox } from './ui/checkbox';
import { Label } from './ui/label';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';

interface SettingsPanelProps {
    usePalantirMode: boolean;
    onPalantirModeChange: (value: boolean) => void;
    selectedCOATypes: string[];
    onCOATypesChange: (types: string[]) => void;
}

const COA_TYPES = [
    { value: 'Defense', label: '방어' },
    { value: 'Offensive', label: '공세' },
    { value: 'Counter_Attack', label: '반격' },
    { value: 'Preemptive', label: '선제' },
    { value: 'Deterrence', label: '억제' },
    { value: 'Maneuver', label: '기동' },
    { value: 'Information_Ops', label: '정보작전' }
];

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
    usePalantirMode,
    onPalantirModeChange,
    selectedCOATypes,
    onCOATypesChange
}) => {
    const [showDetails, setShowDetails] = useState(false);

    const handleCOATypeToggle = (type: string) => {
        if (selectedCOATypes.includes(type)) {
            onCOATypesChange(selectedCOATypes.filter(t => t !== type));
        } else {
            onCOATypesChange([...selectedCOATypes, type]);
        }
    };

    return (
        <div className="space-y-4">
            {/* 팔란티어 모드 설정 */}
            <Card className="border-gray-200 dark:border-zinc-700">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                        팔란티어 모드
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id="palantir-mode"
                            checked={usePalantirMode}
                            onCheckedChange={(checked) => onPalantirModeChange(checked === true)}
                        />
                        <Label
                            htmlFor="palantir-mode"
                            className="text-sm font-medium cursor-pointer text-gray-700 dark:text-gray-300"
                        >
                            팔란티어 모드 활성화
                        </Label>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
                        다중 요소 기반 종합 점수 계산 (위협, 자원, 자산, 환경, 과거, 체인) + RAG 검색 활용
                    </p>
                    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-2">
                        <p className="text-xs text-blue-700 dark:text-blue-300">
                            💡 참고: RAG 검색은 항상 활성화됩니다 (과거 사례 활용 및 LLM 컨텍스트 제공)
                        </p>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setShowDetails(!showDetails)}
                        className="w-full text-xs"
                    >
                        {showDetails ? '상세 정보 숨기기' : '상세 정보 보기'}
                    </Button>
                    {showDetails && (
                        <div className="mt-2 p-3 bg-gray-50 dark:bg-zinc-800 rounded-lg text-xs space-y-2">
                            <p className="font-semibold text-gray-700 dark:text-gray-300">팔란티어 모드 특징:</p>
                            <ul className="list-disc list-inside space-y-1 text-gray-600 dark:text-gray-400">
                                <li>6개 요소 종합 평가 (위협/자원/자산/환경/과거/체인)</li>
                                <li>SPARQL 쿼리로 그래프 관계 분석</li>
                                <li>RAG 검색으로 과거 성공률 계산</li>
                                <li>다단계 관계 체인 탐색</li>
                                <li>각 요소별 점수 breakdown 제공</li>
                            </ul>
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* 방책 유형 필터 */}
            <Card className="border-gray-200 dark:border-zinc-700">
                <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                        방책 유형 필터
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                        선택한 유형의 방책만 추천 결과에 포함됩니다.
                    </p>
                    <div className="space-y-2">
                        {COA_TYPES.map((type) => (
                            <div key={type.value} className="flex items-center space-x-2">
                                <Checkbox
                                    id={`coa-type-${type.value}`}
                                    checked={selectedCOATypes.includes(type.value)}
                                    onCheckedChange={() => handleCOATypeToggle(type.value)}
                                />
                                <Label
                                    htmlFor={`coa-type-${type.value}`}
                                    className="text-sm cursor-pointer text-gray-700 dark:text-gray-300"
                                >
                                    {type.label}
                                </Label>
                            </div>
                        ))}
                    </div>
                    <div className="mt-3 pt-3 border-t border-gray-200 dark:border-zinc-700">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onCOATypesChange(COA_TYPES.map(t => t.value))}
                            className="w-full text-xs"
                        >
                            전체 선택
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
};
