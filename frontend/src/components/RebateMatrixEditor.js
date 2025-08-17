import React, { useState } from 'react';
import './RebateMatrixEditor.css';

const RebateMatrixEditor = ({ matrix, onChange, disabled }) => {
    const [newRow, setNewRow] = useState({
        plan_range: '30000',
        contract_period: 3,
        rebate_amount: 0
    });

    const planRanges = [
        { value: '30000', label: '3만원대' },
        { value: '50000', label: '5만원대' },
        { value: '70000', label: '7만원대' },
        { value: '100000', label: '10만원대' },
        { value: '150000', label: '15만원대' }
    ];

    const contractPeriods = [3, 6, 9, 12, 24];

    const handleNewRowChange = (field, value) => {
        setNewRow(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const handleAddRow = () => {
        // 중복 체크
        const isDuplicate = matrix.some(
            item => item.plan_range === newRow.plan_range && 
                   item.contract_period === Number(newRow.contract_period)
        );

        if (isDuplicate) {
            alert('이미 동일한 요금제와 계약기간의 리베이트가 존재합니다.');
            return;
        }

        if (newRow.rebate_amount <= 0) {
            alert('리베이트 금액을 입력해주세요.');
            return;
        }

        const updatedMatrix = [...matrix, {
            ...newRow,
            contract_period: Number(newRow.contract_period),
            rebate_amount: Number(newRow.rebate_amount)
        }];

        onChange(updatedMatrix);

        // 입력 필드 초기화
        setNewRow({
            plan_range: '30000',
            contract_period: 3,
            rebate_amount: 0
        });
    };

    const handleRemoveRow = (index) => {
        const updatedMatrix = matrix.filter((_, i) => i !== index);
        onChange(updatedMatrix);
    };

    const formatAmount = (amount) => {
        return new Intl.NumberFormat('ko-KR').format(amount);
    };

    const getPlanLabel = (value) => {
        const plan = planRanges.find(p => p.value === value);
        return plan ? plan.label : value;
    };

    return (
        <div className="rebate-matrix-editor">
            <div className="matrix-table">
                <table>
                    <thead>
                        <tr>
                            <th>요금제</th>
                            <th>계약기간</th>
                            <th>리베이트 금액</th>
                            <th>작업</th>
                        </tr>
                    </thead>
                    <tbody>
                        {matrix.map((row, index) => (
                            <tr key={index}>
                                <td>{getPlanLabel(row.plan_range)}</td>
                                <td>{row.contract_period}개월</td>
                                <td>{formatAmount(row.rebate_amount)}원</td>
                                <td>
                                    <button
                                        type="button"
                                        className="btn btn-small btn-danger"
                                        onClick={() => handleRemoveRow(index)}
                                        disabled={disabled}
                                    >
                                        삭제
                                    </button>
                                </td>
                            </tr>
                        ))}
                        {matrix.length === 0 && (
                            <tr>
                                <td colSpan="4" className="no-data">
                                    리베이트 매트릭스가 설정되지 않았습니다.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            <div className="add-row-form">
                <h4>리베이트 추가</h4>
                <div className="form-row">
                    <div className="form-group">
                        <label>요금제</label>
                        <select
                            value={newRow.plan_range}
                            onChange={(e) => handleNewRowChange('plan_range', e.target.value)}
                            disabled={disabled}
                        >
                            {planRanges.map(plan => (
                                <option key={plan.value} value={plan.value}>
                                    {plan.label}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label>계약기간</label>
                        <select
                            value={newRow.contract_period}
                            onChange={(e) => handleNewRowChange('contract_period', e.target.value)}
                            disabled={disabled}
                        >
                            {contractPeriods.map(period => (
                                <option key={period} value={period}>
                                    {period}개월
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label>리베이트 금액</label>
                        <input
                            type="number"
                            value={newRow.rebate_amount}
                            onChange={(e) => handleNewRowChange('rebate_amount', e.target.value)}
                            disabled={disabled}
                            placeholder="0"
                            min="0"
                        />
                    </div>

                    <div className="form-group">
                        <label>&nbsp;</label>
                        <button
                            type="button"
                            className="btn btn-primary"
                            onClick={handleAddRow}
                            disabled={disabled}
                        >
                            추가
                        </button>
                    </div>
                </div>
            </div>

            <div className="matrix-summary">
                <h4>리베이트 매트릭스 요약</h4>
                <div className="summary-grid">
                    {planRanges.map(plan => {
                        const planItems = matrix.filter(item => item.plan_range === plan.value);
                        if (planItems.length === 0) return null;
                        
                        return (
                            <div key={plan.value} className="summary-item">
                                <h5>{plan.label}</h5>
                                <ul>
                                    {planItems.map((item, idx) => (
                                        <li key={idx}>
                                            {item.contract_period}개월: {formatAmount(item.rebate_amount)}원
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default RebateMatrixEditor;
