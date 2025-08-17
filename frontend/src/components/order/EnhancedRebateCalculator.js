import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Typography, Divider, Spin, Alert } from 'antd';
import { CalculatorOutlined, DollarOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { get } from '../../services/api';

const { Text, Title } = Typography;

const EnhancedRebateCalculator = ({ 
  policyId, 
  carrierPlan, 
  contractPeriod, 
  simType, 
  formValues 
}) => {
  const [rebateData, setRebateData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (policyId && carrierPlan && contractPeriod) {
      calculateRebate();
    } else {
      setRebateData(null);
    }
  }, [policyId, carrierPlan, contractPeriod, simType]);

  const calculateRebate = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await get('api/policies/calculate-rebate/', {
        policy_id: policyId,
        carrier_plan_id: carrierPlan,
        contract_period: contractPeriod,
        sim_type: simType || 'postpaid'
      });

      if (response.success && response.data) {
        let data = response.data;
        
        // 이중래핑 처리
        if (data.data && typeof data.data === 'object') {
          console.log('[EnhancedRebateCalculator] 이중래핑 감지, data.data 사용');
          data = data.data;
        }
        
        console.log('[EnhancedRebateCalculator] 리베이트 계산 결과:', data);
        setRebateData(data);
      } else {
        console.error('[EnhancedRebateCalculator] 리베이트 계산 실패:', response);
        setError('리베이트 계산에 실패했습니다.');
      }
    } catch (err) {
      console.error('리베이트 계산 오류:', err);
      setError('리베이트 계산 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const getSimAdjustmentColor = (adjustment) => {
    if (adjustment > 0) return '#52c41a'; // 초록색 (플러스)
    if (adjustment < 0) return '#ff4d4f'; // 빨간색 (마이너스)
    return '#8c8c8c'; // 회색 (0)
  };

  const getSimAdjustmentIcon = (adjustment) => {
    if (adjustment > 0) return '+';
    if (adjustment < 0) return '';
    return '';
  };

  if (!policyId || !carrierPlan || !contractPeriod) {
    return (
      <Card 
        title={
          <span>
            <CalculatorOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            리베이트 계산기
          </span>
        }
        className="rebate-calculator-card"
        style={{ marginTop: 24 }}
      >
        <div style={{ textAlign: 'center', padding: '40px 20px', color: '#8c8c8c' }}>
          <InfoCircleOutlined style={{ fontSize: 48, marginBottom: 16 }} />
          <Text type="secondary">
            요금제와 계약기간을 선택하면 리베이트가 자동으로 계산됩니다.
          </Text>
        </div>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card 
        title={
          <span>
            <CalculatorOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            리베이트 계산기
          </span>
        }
        className="rebate-calculator-card"
        style={{ marginTop: 24 }}
      >
        <div style={{ textAlign: 'center', padding: '40px 20px' }}>
          <Spin size="large" />
          <Text style={{ display: 'block', marginTop: 16 }}>
            리베이트를 계산하고 있습니다...
          </Text>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card 
        title={
          <span>
            <CalculatorOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            리베이트 계산기
          </span>
        }
        className="rebate-calculator-card"
        style={{ marginTop: 24 }}
      >
        <Alert
          message="계산 오류"
          description={error}
          type="error"
          showIcon
        />
      </Card>
    );
  }

  if (!rebateData) return null;

  return (
    <Card 
      title={
        <span>
          <CalculatorOutlined style={{ marginRight: 8, color: '#1890ff' }} />
          리베이트 계산기
        </span>
      }
      className="rebate-calculator-card enhanced"
      style={{ 
        marginTop: 24,
        border: '2px solid #e6f7ff',
        borderRadius: 12
      }}
      headStyle={{ 
        background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
        color: 'white',
        borderRadius: '10px 10px 0 0'
      }}
    >
      {/* 계산 과정 표시 */}
      <div className="calculation-process" style={{ marginBottom: 24 }}>
        <Title level={5} style={{ color: '#1890ff', marginBottom: 16 }}>
          📊 계산 과정
        </Title>
        
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={6}>
            <div className="calculation-step">
              <Text strong style={{ color: '#52c41a' }}>기본 리베이트</Text>
              <div style={{ 
                fontSize: '20px', 
                fontWeight: 700, 
                color: '#52c41a',
                marginTop: 4
              }}>
                {rebateData.base_rebate?.toLocaleString()}원
              </div>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                요금제별 기본금액
              </Text>
            </div>
          </Col>

          <Col xs={24} sm={1} style={{ textAlign: 'center' }}>
            <Text style={{ fontSize: '18px', color: '#8c8c8c' }}>×</Text>
          </Col>

          <Col xs={24} sm={5}>
            <div className="calculation-step">
              <Text strong style={{ color: '#fa8c16' }}>계약기간 가중치</Text>
              <div style={{ 
                fontSize: '20px', 
                fontWeight: 700, 
                color: '#fa8c16',
                marginTop: 4
              }}>
                ×{rebateData.period_multiplier}
              </div>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {contractPeriod}개월 계약
              </Text>
            </div>
          </Col>

          <Col xs={24} sm={1} style={{ textAlign: 'center' }}>
            <Text style={{ fontSize: '18px', color: '#8c8c8c' }}>=</Text>
          </Col>

          <Col xs={24} sm={5}>
            <div className="calculation-step">
              <Text strong style={{ color: '#722ed1' }}>계산된 리베이트</Text>
              <div style={{ 
                fontSize: '20px', 
                fontWeight: 700, 
                color: '#722ed1',
                marginTop: 4
              }}>
                {rebateData.calculated_rebate?.toLocaleString()}원
              </div>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                기본 × 가중치
              </Text>
            </div>
          </Col>

          <Col xs={24} sm={1} style={{ textAlign: 'center' }}>
            <Text style={{ fontSize: '18px', color: '#8c8c8c' }}>
              {rebateData.sim_adjustment >= 0 ? '+' : ''}
            </Text>
          </Col>

          <Col xs={24} sm={5}>
            <div className="calculation-step">
              <Text strong style={{ color: getSimAdjustmentColor(rebateData.sim_adjustment) }}>
                유심비 조정
              </Text>
              <div style={{ 
                fontSize: '20px', 
                fontWeight: 700, 
                color: getSimAdjustmentColor(rebateData.sim_adjustment),
                marginTop: 4
              }}>
                {getSimAdjustmentIcon(rebateData.sim_adjustment)}{Math.abs(rebateData.sim_adjustment)?.toLocaleString()}원
              </div>
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {simType === 'prepaid' ? '선불 지급' : simType === 'postpaid' ? '후불 차감' : '조정 없음'}
              </Text>
            </div>
          </Col>
        </Row>
      </div>

      <Divider />

      {/* 최종 결과 */}
      <div className="final-result" style={{ textAlign: 'center', padding: '20px 0' }}>
        <Title level={4} style={{ color: '#1890ff', marginBottom: 8 }}>
          🎯 최종 리베이트
        </Title>
        <div style={{ 
          fontSize: '32px', 
          fontWeight: 800, 
          color: '#1890ff',
          textShadow: '0 2px 4px rgba(24, 144, 255, 0.2)',
          marginBottom: 8
        }}>
          {rebateData.final_rebate?.toLocaleString()}원
        </div>
        <Text type="secondary">
          위 금액이 판매점에 지급되는 최종 리베이트입니다.
        </Text>
      </div>

      {/* 상세 정보 */}
      {rebateData.details && (
        <div className="rebate-details" style={{ 
          marginTop: 16,
          padding: 16,
          background: '#fafafa',
          borderRadius: 8,
          border: '1px solid #f0f0f0'
        }}>
          <Text strong style={{ color: '#595959', marginBottom: 8, display: 'block' }}>
            📋 상세 정보
          </Text>
          <Row gutter={16}>
            <Col span={8}>
              <Text type="secondary">요금제명:</Text>
              <br />
              <Text strong>{rebateData.details.plan_name}</Text>
            </Col>
            <Col span={8}>
              <Text type="secondary">요금제 가격:</Text>
              <br />
              <Text strong>{rebateData.details.plan_price?.toLocaleString()}원</Text>
            </Col>
            <Col span={8}>
              <Text type="secondary">통신사:</Text>
              <br />
              <Text strong>{rebateData.details.carrier}</Text>
            </Col>
          </Row>
        </div>
      )}
    </Card>
  );
};

export default EnhancedRebateCalculator;
