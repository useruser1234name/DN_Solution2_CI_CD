import React, { useState, useEffect } from 'react';
import { Select, Spin, message } from 'antd';
import { get } from '../../services/api';
import './CarrierPlanSelector.css';

const { Option } = Select;

const CarrierPlanSelector = ({ 
  value, 
  onChange, 
  carrier, 
  placeholder = "요금제를 선택하세요",
  disabled = false,
  allowClear = true,
  onPlanSelect = null // 요금제 선택 시 추가 콜백
}) => {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);

  // 통신사별 요금제 로드
  const loadCarrierPlans = async (carrierCode) => {
    if (!carrierCode) {
      setPlans([]);
      return;
    }

    setLoading(true);
    try {
      const response = await get(`/api/policies/carrier-plans/?carrier=${carrierCode}&is_active=true`);
      if (response.success) {
        setPlans(response.data || []);
      } else {
        message.error('요금제 정보를 불러오는데 실패했습니다.');
        setPlans([]);
      }
    } catch (error) {
      console.error('요금제 로드 오류:', error);
      message.error('요금제 정보를 불러오는 중 오류가 발생했습니다.');
      setPlans([]);
    } finally {
      setLoading(false);
    }
  };

  // 통신사 변경 시 요금제 로드
  useEffect(() => {
    loadCarrierPlans(carrier);
  }, [carrier]);

  // 통신사 변경 시 선택된 요금제 초기화
  useEffect(() => {
    if (value && carrier) {
      // 현재 선택된 요금제가 새로운 통신사의 요금제인지 확인
      const currentPlan = plans.find(plan => plan.id === value);
      if (!currentPlan) {
        onChange(null);
      }
    }
  }, [carrier, plans, value, onChange]);

  const handlePlanChange = (planId, option) => {
    onChange(planId);
    
    // 선택된 요금제 정보를 부모 컴포넌트에 전달
    if (onPlanSelect && option) {
      const planData = plans.find(plan => plan.id === planId);
      onPlanSelect(planData);
    }
  };

  const formatPlanOption = (plan) => {
    return `${plan.plan_name} (${plan.plan_price.toLocaleString()}원)`;
  };

  return (
    <div className="carrier-plan-selector">
      <Select
        value={value}
        onChange={handlePlanChange}
        placeholder={carrier ? placeholder : "먼저 통신사를 선택하세요"}
        disabled={disabled || !carrier || loading}
        allowClear={allowClear}
        loading={loading}
        showSearch
        filterOption={(input, option) =>
          option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
        }
        style={{ width: '100%' }}
        notFoundContent={loading ? <Spin size="small" /> : '요금제가 없습니다'}
      >
        {plans.map(plan => (
          <Option key={plan.id} value={plan.id} title={plan.description}>
            {formatPlanOption(plan)}
          </Option>
        ))}
      </Select>
      
      {carrier && plans.length === 0 && !loading && (
        <div className="no-plans-message">
          해당 통신사의 요금제가 등록되지 않았습니다.
        </div>
      )}
    </div>
  );
};

export default CarrierPlanSelector;

