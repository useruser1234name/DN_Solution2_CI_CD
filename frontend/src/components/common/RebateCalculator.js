import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Spin, Alert, Typography, Divider } from 'antd';
import { CalculatorOutlined, DollarOutlined } from '@ant-design/icons';
import { get } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import './RebateCalculator.css';

const { Text, Title } = Typography;

const RebateCalculator = ({ 
  policyId,
  carrier,
  planId,
  contractPeriod,
  simType,
  onRebateCalculated = null
}) => {
  const [rebateData, setRebateData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { user, isHeadquarters, isAgency, isRetail } = useAuth();

  // 리베이트 계산
  const calculateRebate = async () => {
    if (!policyId || !carrier || !planId || !contractPeriod) {
      setRebateData(null);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await get('/api/policies/calculate-rebate/', {
        policy_id: policyId,
        carrier: carrier,
        plan_id: planId,
        contract_period: contractPeriod,
        sim_type: simType
      });

      if (response.success) {
        setRebateData(response.data);
        
        // 부모 컴포넌트에 계산 결과 전달
        if (onRebateCalculated) {
          onRebateCalculated(response.data);
        }
      } else {
        setError(response.message || '리베이트 계산에 실패했습니다.');
        setRebateData(null);
      }
    } catch (error) {
      console.error('리베이트 계산 오류:', error);
      setError('리베이트 계산 중 오류가 발생했습니다.');
      setRebateData(null);
    } finally {
      setLoading(false);
    }
  };

  // 의존성 변경 시 리베이트 재계산
  useEffect(() => {
    calculateRebate();
  }, [policyId, carrier, planId, contractPeriod, simType]);

  // 유심비 계산
  const getSimCost = () => {
    if (!simType || simType === 'reuse' || simType === 'esim') {
      return 0;
    }
    return simType === 'prepaid' ? 7700 : -7700; // 선불: +7700, 후불: -7700
  };

  // 사용자 타입에 따른 리베이트 표시
  const getRebateForUser = () => {
    if (!rebateData) return null;

    const simCost = getSimCost();
    
    if (isHeadquarters()) {
      // 본사: 협력사 리베이트만 표시 (판매점 리베이트는 관심 없음)
      return {
        agency: rebateData.agency_rebate + simCost,
        showRetail: false
      };
    } else if (isAgency()) {
      // 협력사: 본인이 받을 리베이트와 판매점에 줄 리베이트 표시
      return {
        agency: rebateData.agency_rebate + simCost,
        retail: rebateData.retail_rebate,
        showRetail: true
      };
    } else if (isRetail()) {
      // 판매점: 본인이 받을 리베이트만 표시
      return {
        retail: rebateData.retail_rebate,
        showRetail: true,
        showAgency: false
      };
    }
    
    return null;
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'KRW'
    }).format(amount);
  };

  const userRebate = getRebateForUser();
  const simCost = getSimCost();

  if (!policyId || !carrier || !planId || !contractPeriod) {
    return (
      <Card className="rebate-calculator empty-state">
        <div className="empty-content">
          <CalculatorOutlined className="empty-icon" />
          <Text type="secondary">
            정책, 통신사, 요금제, 계약기간을 모두 선택하면<br />
            리베이트가 자동으로 계산됩니다.
          </Text>
        </div>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card className="rebate-calculator loading-state">
        <div className="loading-content">
          <Spin size="large" />
          <Text style={{ marginTop: 16 }}>리베이트 계산 중...</Text>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="rebate-calculator error-state">
        <Alert
          message="리베이트 계산 오류"
          description={error}
          type="error"
          showIcon
        />
      </Card>
    );
  }

  if (!userRebate) {
    return (
      <Card className="rebate-calculator no-data-state">
        <Alert
          message="리베이트 정보 없음"
          description="해당 조건에 대한 리베이트 정보가 설정되지 않았습니다."
          type="warning"
          showIcon
        />
      </Card>
    );
  }

  return (
    <Card 
      className="rebate-calculator"
      title={
        <div className="calculator-title">
          <DollarOutlined />
          <span>리베이트 계산 결과</span>
        </div>
      }
    >
      <div className="rebate-content">
        {/* 본사 또는 협력사가 받을 리베이트 */}
        {userRebate.agency !== undefined && (
          <div className="rebate-section">
            <Row justify="space-between" align="middle">
              <Col>
                <Text strong>
                  {isHeadquarters() ? '협력사 지급 리베이트' : '수령 리베이트'}
                </Text>
              </Col>
              <Col>
                <Title level={4} className="rebate-amount positive">
                  {formatCurrency(userRebate.agency)}
                </Title>
              </Col>
            </Row>
            
            {simCost !== 0 && (
              <div className="sim-cost-detail">
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  기본 리베이트: {formatCurrency(rebateData.agency_rebate)} 
                  {simCost > 0 ? ' + ' : ' - '}
                  유심비: {formatCurrency(Math.abs(simCost))}
                </Text>
              </div>
            )}
          </div>
        )}

        {/* 판매점 리베이트 (협력사만 표시) */}
        {userRebate.showRetail && userRebate.retail !== undefined && (
          <>
            <Divider />
            <div className="rebate-section">
              <Row justify="space-between" align="middle">
                <Col>
                  <Text strong>
                    {isAgency() ? '판매점 지급 리베이트' : '수령 리베이트'}
                  </Text>
                </Col>
                <Col>
                  <Title level={4} className="rebate-amount positive">
                    {formatCurrency(userRebate.retail)}
                  </Title>
                </Col>
              </Row>
            </div>
          </>
        )}

        {/* 유심 타입 정보 */}
        {simType && simType !== 'reuse' && (
          <div className="sim-info">
            <Divider />
            <Row justify="space-between" align="middle">
              <Col>
                <Text type="secondary">유심 타입</Text>
              </Col>
              <Col>
                <Text>
                  {simType === 'prepaid' && '선불 (+7,700원)'}
                  {simType === 'postpaid' && '후불 (-7,700원)'}
                  {simType === 'esim' && 'eSIM (추가비용 없음)'}
                </Text>
              </Col>
            </Row>
          </div>
        )}

        {/* 계산 기준 정보 */}
        <div className="calculation-info">
          <Divider />
          <Text type="secondary" style={{ fontSize: '12px' }}>
            * 계산 기준: {contractPeriod}개월 약정, {rebateData.plan_name || '선택된 요금제'}
          </Text>
        </div>
      </div>
    </Card>
  );
};

export default RebateCalculator;

