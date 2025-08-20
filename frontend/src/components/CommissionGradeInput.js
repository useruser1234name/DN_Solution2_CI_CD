import React, { useState } from 'react';
import './CommissionGradeInput.css';

const CommissionGradeInput = ({ value = [], onChange, disabled = false, title = "수수료 그레이드 설정" }) => {
    const [showGradePanel, setShowGradePanel] = useState(false);

    const addGrade = () => {
        const newGrade = {
            id: Date.now(),
            min_orders: '',
            bonus_per_order: '',
            description: ''
        };
        onChange([...value, newGrade]);
        setShowGradePanel(true);
    };

    const updateGrade = (index, field, fieldValue) => {
        const updatedGrades = value.map((grade, i) => {
            if (i === index) {
                return {
                    ...grade,
                    [field]: fieldValue
                };
            }
            return grade;
        });
        onChange(updatedGrades);
    };

    const removeGrade = (index) => {
        const updatedGrades = value.filter((_, i) => i !== index);
        onChange(updatedGrades);
        
        // 그레이드가 모두 삭제되면 패널 숨김
        if (updatedGrades.length === 0) {
            setShowGradePanel(false);
        }
    };

    const formatNumber = (num) => {
        return num ? Number(num).toLocaleString() : '0';
    };

    const totalGrades = value.length;
    const validGrades = value.filter(g => g.min_orders && g.bonus_per_order).length;

    return (
        <div className="commission-grade-input">
            <div className="grade-header">
                <h3>{title}</h3>
                <div className="grade-summary">
                    {totalGrades > 0 && (
                        <span className="grade-count">
                            총 {totalGrades}개 그레이드 (유효: {validGrades}개)
                        </span>
                    )}
                </div>
            </div>

            <div className="grade-description">
                <p>주문량에 따른 추가 수수료를 설정할 수 있습니다. 설정된 주문량을 달성하면 건당 보너스 수수료가 추가로 지급됩니다.</p>
            </div>

            {/* 그레이드 추가 버튼 */}
            <div className="grade-actions">
                <button
                    type="button"
                    onClick={addGrade}
                    disabled={disabled}
                    className="btn btn-primary add-grade-btn"
                >
                    + 그레이드 추가
                </button>
                
                {totalGrades > 0 && (
                    <button
                        type="button"
                        onClick={() => setShowGradePanel(!showGradePanel)}
                        className="btn btn-secondary toggle-panel-btn"
                    >
                        {showGradePanel ? '그레이드 숨기기' : '그레이드 보기'}
                    </button>
                )}
            </div>

            {/* 그레이드 목록 표시 */}
            {(showGradePanel || totalGrades === 0) && (
                <div className="grade-list">
                    {value.length === 0 ? (
                        <div className="empty-grades">
                            <p>설정된 그레이드가 없습니다.</p>
                            <p>첫 번째 그레이드를 추가해보세요.</p>
                        </div>
                    ) : (
                        <div className="grade-items">
                            {value.map((grade, index) => (
                                <div key={grade.id || index} className="grade-item">
                                    <div className="grade-item-header">
                                        <h4>그레이드 {index + 1}</h4>
                                        <button
                                            type="button"
                                            onClick={() => removeGrade(index)}
                                            disabled={disabled}
                                            className="btn btn-danger remove-grade-btn"
                                        >
                                            삭제
                                        </button>
                                    </div>

                                    <div className="grade-fields">
                                        <div className="field-row">
                                            <div className="form-group">
                                                <label>최소 주문건수 *</label>
                                                <input
                                                    type="number"
                                                    value={grade.min_orders}
                                                    onChange={(e) => updateGrade(index, 'min_orders', parseInt(e.target.value) || '')}
                                                    disabled={disabled}
                                                    placeholder="10"
                                                    min="1"
                                                />
                                                <span className="field-hint">이 그레이드를 달성하기 위한 최소 주문 건수</span>
                                            </div>

                                            <div className="form-group">
                                                <label>건당 보너스 수수료 (원) *</label>
                                                <input
                                                    type="number"
                                                    value={grade.bonus_per_order}
                                                    onChange={(e) => updateGrade(index, 'bonus_per_order', parseInt(e.target.value) || '')}
                                                    disabled={disabled}
                                                    placeholder="5000"
                                                    min="0"
                                                    step="1000"
                                                />
                                                <span className="field-hint">그레이드 달성 시 건당 추가 지급 수수료</span>
                                            </div>
                                        </div>

                                        <div className="form-group">
                                            <label>그레이드 설명</label>
                                            <input
                                                type="text"
                                                value={grade.description || ''}
                                                onChange={(e) => updateGrade(index, 'description', e.target.value)}
                                                disabled={disabled}
                                                placeholder="예: 월 10건 이상 달성 시"
                                            />
                                            <span className="field-hint">그레이드에 대한 간단한 설명 (선택사항)</span>
                                        </div>

                                        {/* 그레이드 미리보기 */}
                                        {grade.min_orders && grade.bonus_per_order && (
                                            <div className="grade-preview">
                                                <div className="preview-content">
                                                    <strong>미리보기:</strong> {grade.min_orders}건 이상 달성 시 건당 +{formatNumber(grade.bonus_per_order)}원 추가 지급
                                                    {grade.description && <span className="preview-desc"> ({grade.description})</span>}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* 그레이드 요약 정보 */}
            {totalGrades > 0 && (
                <div className="grade-summary-panel">
                    <h4>그레이드 요약</h4>
                    <div className="summary-content">
                        {value
                            .filter(g => g.min_orders && g.bonus_per_order)
                            .sort((a, b) => a.min_orders - b.min_orders)
                            .map((grade, index) => (
                                <div key={index} className="summary-item">
                                    <span className="summary-text">
                                        {grade.min_orders}건 이상: +{formatNumber(grade.bonus_per_order)}원/건
                                    </span>
                                </div>
                            ))
                        }
                    </div>
                    
                    {validGrades === 0 && totalGrades > 0 && (
                        <div className="summary-warning">
                            ⚠️ 최소 주문건수와 보너스 수수료를 모두 입력해주세요.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default CommissionGradeInput;