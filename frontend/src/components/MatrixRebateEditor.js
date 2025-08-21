import React, { useState, useEffect } from 'react';
import { Card, Table, InputNumber, Typography, Space, Button, message, Modal, Input, Select } from 'antd';
import { DollarOutlined, PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import './MatrixRebateEditor.css';

const { Title, Text } = Typography;
const { Option } = Select;

const MatrixRebateEditor = ({ matrix = [], onChange, disabled = false, carrier = 'KT' }) => {
  const [matrixData, setMatrixData] = useState({});
  
  // 동적 요금제 관리 (기본 9개)
  const [planRanges, setPlanRanges] = useState([
    { value: 11000, label: '11K' },
    { value: 22000, label: '22K' },
    { value: 33000, label: '33K' },
    { value: 44000, label: '44K' },
    { value: 55000, label: '55K' },
    { value: 66000, label: '66K' },
    { value: 77000, label: '77K' },
    { value: 88000, label: '88K' },
    { value: 99000, label: '99K' },
  ]);

  // 동적 계약기간 관리 (기본 3개)
  const [contractPeriods, setContractPeriods] = useState([12, 24, 36]);
  
  // 모달 상태
  const [addRowModal, setAddRowModal] = useState(false);
  const [addColumnModal, setAddColumnModal] = useState(false);
  const [newPlanValue, setNewPlanValue] = useState('');
  const [newPlanLabel, setNewPlanLabel] = useState('');
  const [newPeriod, setNewPeriod] = useState('');

  useEffect(() => {
    console.log('[MatrixRebateEditor] matrix prop 변경됨:', matrix);
    console.log('[MatrixRebateEditor] matrix 타입:', typeof matrix);
    console.log('[MatrixRebateEditor] matrix 길이:', matrix ? matrix.length : 'undefined');
    
    // 기존 매트릭스 데이터를 테이블 형태로 변환
    const newMatrixData = {};
    
    planRanges.forEach(plan => {
      contractPeriods.forEach(period => {
        const key = `${plan.value}_${period}`;
        // plan_range 값은 과거 데이터에서 '11K' 와 같이 문자열로 저장되어 있을 수 있으므로
        // 숫자(11000)·라벨('11K')·숫자 문자열("11000") 모두 비교하도록 범위를 확장합니다.
        const existingItem = matrix.find(item => {
          const planRangeMatches =
            item.plan_range === plan.value || // 최신 스키마: 숫자형 11000
            item.plan_range === plan.label || // 과거 스키마: 문자열 라벨 '11K'
            Number(item.plan_range) === plan.value; // 숫자 문자열 "11000"

          return planRangeMatches && item.contract_period === period;
        });
        const rebateAmount = existingItem ? existingItem.rebate_amount : 0;
        newMatrixData[key] = rebateAmount;
        
        if (existingItem) {
          console.log(`[MatrixRebateEditor] 매트릭스 항목 발견: ${plan.label}/${period}개월 = ${rebateAmount}`);
        }
      });
    });

    console.log('[MatrixRebateEditor] 변환된 매트릭스 데이터:', newMatrixData);
    setMatrixData(newMatrixData);
  }, [matrix, planRanges, contractPeriods]);

  const handleValueChange = (planValue, period, value) => {
    const key = `${planValue}_${period}`;
    const newMatrixData = {
      ...matrixData,
      [key]: value || 0
    };
    setMatrixData(newMatrixData);

    // 부모 컴포넌트에 변경사항 전달
    const newMatrix = [];
    planRanges.forEach(plan => {
      contractPeriods.forEach(contractPeriod => {
        const matrixKey = `${plan.value}_${contractPeriod}`;
        const amount = newMatrixData[matrixKey] || 0;
        if (amount > 0) {
          newMatrix.push({
            plan_range: plan.value,
            contract_period: contractPeriod,
            rebate_amount: amount,
            carrier: carrier.toLowerCase()
          });
        }
      });
    });

    onChange(newMatrix);
  };

  const formatNumber = (value) => {
    return value ? value.toLocaleString() : '0';
  };

  // 동적 컬럼 생성
  const columns = [
    {
      title: (
        <Space>
          <span>요금제</span>
          <Button 
            type="text" 
            size="small" 
            icon={<PlusOutlined />}
            onClick={() => setAddRowModal(true)}
            disabled={disabled}
            title="요금제 추가"
            tabIndex={-1}
          />
        </Space>
      ),
      dataIndex: 'plan',
      key: 'plan',
      width: 120,
      align: 'center',
      render: (text, record) => (
        <Space>
          <div style={{ 
            fontWeight: 'bold', 
            color: '#1890ff',
            fontSize: '16px'
          }}>
            {record.planLabel}
          </div>
          {planRanges.length > 1 && (
            <Button 
              type="text" 
              size="small" 
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('[MatrixRebateEditor] 요금제 삭제 버튼 클릭:', record.planValue);
                handleDeleteRow(record.planValue);
              }}
              disabled={disabled}
              danger
              title={`요금제 삭제 (현재 ${planRanges.length}개)`}
              tabIndex={-1}
            />
          )}
        </Space>
      ),
    },
    // 동적으로 계약기간 컬럼 생성
    ...contractPeriods.map(period => ({
      title: (
        <Space>
          <span>{period}개월</span>
          <Button 
            type="text" 
            size="small" 
            icon={<DeleteOutlined />}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              console.log('[MatrixRebateEditor] 삭제 버튼 클릭:', period);
              handleDeleteColumn(period);
            }}
            disabled={disabled || contractPeriods.length <= 1}
            danger
            title={`계약기간 삭제 (현재 ${contractPeriods.length}개)`}
            tabIndex={-1}
          />
        </Space>
      ),
      dataIndex: `period${period}`,
      key: `period${period}`,
      width: 180,
      align: 'center',
      render: (text, record) => {
        // 탭 순서 계산: 행 인덱스 * 열 개수 + 열 인덱스 + 1
        const rowIndex = planRanges.findIndex(plan => plan.value === record.planValue);
        const colIndex = contractPeriods.findIndex(p => p === period);
        const tabIndex = rowIndex * contractPeriods.length + colIndex + 1;
        
        return (
          <InputNumber
            value={matrixData[`${record.planValue}_${period}`] || 0}
            onChange={(value) => handleValueChange(record.planValue, period, value)}
            disabled={disabled}
            style={{ width: '100%' }}
            formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            parser={value => value.replace(/\$\s?|(,*)/g, '')}
            min={0}
            step={1000}
            placeholder="0"
            tabIndex={tabIndex}
          />
        );
      },
    })),
    // 계약기간 추가 컬럼
    {
      title: (
        <Button 
          type="dashed" 
          size="small" 
          icon={<PlusOutlined />}
          onClick={() => setAddColumnModal(true)}
          disabled={disabled}
          title="계약기간 추가"
          tabIndex={-1}
        >
          기간 추가
        </Button>
      ),
      key: 'addColumn',
      width: 100,
      align: 'center',
      render: () => null,
    },
  ];

  const dataSource = planRanges.map(plan => ({
    key: plan.value,
    planValue: plan.value,
    planLabel: plan.label,
    plan: plan.label,
  }));

  const handleQuickFill = () => {
    // 사용자 예시 데이터로 빠른 채우기
    const quickData = {
      '11000_12': 40000,
      '11000_24': 240000,
      '22000_12': 60000,
      '22000_24': 260000,
      '33000_12': 80000,
      '33000_24': 280000,
      '44000_12': 100000,
      '44000_24': 300000,
      '55000_12': 120000,
      '55000_24': 320000,
      '66000_12': 140000,
      '66000_24': 340000,
      '77000_12': 160000,
      '77000_24': 360000,
      '88000_12': 180000,
      '88000_24': 380000,
      '99000_12': 200000,
      '99000_24': 400000,
    };

    setMatrixData(quickData);

    // 부모 컴포넌트에 전달
    const newMatrix = [];
    planRanges.forEach(plan => {
      contractPeriods.forEach(period => {
        const key = `${plan.value}_${period}`;
        const amount = quickData[key] || 0;
        if (amount > 0) {
          newMatrix.push({
            plan_range: plan.value,
            contract_period: period,
            rebate_amount: amount,
            carrier: carrier.toLowerCase()
          });
        }
      });
    });

    onChange(newMatrix);
    message.success('예시 데이터로 채워졌습니다!');
  };

  const handleClearAll = () => {
    const emptyData = {};
    planRanges.forEach(plan => {
      contractPeriods.forEach(period => {
        const key = `${plan.value}_${period}`;
        emptyData[key] = 0;
      });
    });

    setMatrixData(emptyData);
    onChange([]);
    message.success('모든 데이터가 초기화되었습니다.');
  };

  // 행(요금제) 추가
  const handleAddRow = () => {
    if (!newPlanValue || !newPlanLabel) {
      message.error('요금제 금액과 라벨을 모두 입력해주세요.');
      return;
    }

    const planValue = parseInt(newPlanValue);
    if (planRanges.some(plan => plan.value === planValue)) {
      message.error('이미 존재하는 요금제입니다.');
      return;
    }

    const newPlan = { value: planValue, label: newPlanLabel };
    const updatedPlanRanges = [...planRanges, newPlan].sort((a, b) => a.value - b.value);
    setPlanRanges(updatedPlanRanges);

    // 새 행에 대한 기본 데이터 추가
    const newMatrixData = { ...matrixData };
    contractPeriods.forEach(period => {
      const key = `${planValue}_${period}`;
      newMatrixData[key] = 0;
    });
    setMatrixData(newMatrixData);

    setAddRowModal(false);
    setNewPlanValue('');
    setNewPlanLabel('');
    message.success(`요금제 ${newPlanLabel}이 추가되었습니다.`);
  };

  // 행(요금제) 삭제
  const handleDeleteRow = (planValue) => {
    console.log('[MatrixRebateEditor] 요금제 삭제 시도:', planValue, '현재 요금제들:', planRanges);
    
    if (planRanges.length <= 1) {
      message.error('최소 1개의 요금제는 유지되어야 합니다.');
      return;
    }

    // 즉시 삭제 (모달 없이)
    try {
      console.log('[MatrixRebateEditor] 요금제 즉시 삭제 시작:', planValue);
      
      const updatedPlanRanges = planRanges.filter(plan => plan.value !== planValue);
      console.log('[MatrixRebateEditor] 업데이트된 요금제들:', updatedPlanRanges);
      
      setPlanRanges(updatedPlanRanges);

      // 해당 행의 데이터 삭제
      const newMatrixData = { ...matrixData };
      contractPeriods.forEach(period => {
        const key = `${planValue}_${period}`;
        delete newMatrixData[key];
        console.log('[MatrixRebateEditor] 삭제된 키:', key);
      });
      setMatrixData(newMatrixData);

      // 부모 컴포넌트에 변경사항 전달
      updateParentMatrix(newMatrixData, updatedPlanRanges, contractPeriods);
      message.success('요금제가 삭제되었습니다.');
      
      console.log('[MatrixRebateEditor] 요금제 삭제 완료');
    } catch (error) {
      console.error('[MatrixRebateEditor] 요금제 삭제 중 오류:', error);
      message.error('삭제 중 오류가 발생했습니다.');
    }
  };

  // 열(계약기간) 추가
  const handleAddColumn = () => {
    if (!newPeriod) {
      message.error('계약기간을 입력해주세요.');
      return;
    }

    const period = parseInt(newPeriod);
    if (contractPeriods.includes(period)) {
      message.error('이미 존재하는 계약기간입니다.');
      return;
    }

    const updatedPeriods = [...contractPeriods, period].sort((a, b) => a - b);
    setContractPeriods(updatedPeriods);

    // 새 열에 대한 기본 데이터 추가
    const newMatrixData = { ...matrixData };
    planRanges.forEach(plan => {
      const key = `${plan.value}_${period}`;
      newMatrixData[key] = 0;
    });
    setMatrixData(newMatrixData);

    setAddColumnModal(false);
    setNewPeriod('');
    message.success(`${period}개월 계약기간이 추가되었습니다.`);
  };

  // 열(계약기간) 삭제
  const handleDeleteColumn = (period) => {
    console.log('[MatrixRebateEditor] 삭제 시도:', period, '현재 기간들:', contractPeriods);
    
    if (contractPeriods.length <= 1) {
      message.error('최소 1개의 계약기간은 유지되어야 합니다.');
      return;
    }

    // 즉시 삭제 (모달 없이)
    try {
      console.log('[MatrixRebateEditor] 즉시 삭제 시작:', period);
      
      const updatedPeriods = contractPeriods.filter(p => p !== period);
      console.log('[MatrixRebateEditor] 업데이트된 기간들:', updatedPeriods);
      
      setContractPeriods(updatedPeriods);

      // 해당 열의 데이터 삭제
      const newMatrixData = { ...matrixData };
      planRanges.forEach(plan => {
        const key = `${plan.value}_${period}`;
        delete newMatrixData[key];
        console.log('[MatrixRebateEditor] 삭제된 키:', key);
      });
      setMatrixData(newMatrixData);

      // 부모 컴포넌트에 변경사항 전달
      updateParentMatrix(newMatrixData, planRanges, updatedPeriods);
      message.success(`${period}개월 계약기간이 삭제되었습니다.`);
      
      console.log('[MatrixRebateEditor] 삭제 완료');
    } catch (error) {
      console.error('[MatrixRebateEditor] 삭제 중 오류:', error);
      message.error('삭제 중 오류가 발생했습니다.');
    }
  };

  // 부모 컴포넌트 업데이트 헬퍼 함수
  const updateParentMatrix = (data, plans, periods) => {
    const newMatrix = [];
    plans.forEach(plan => {
      periods.forEach(period => {
        const key = `${plan.value}_${period}`;
        const amount = data[key] || 0;
        if (amount > 0) {
          newMatrix.push({
            plan_range: plan.value,
            contract_period: period,
            rebate_amount: amount,
            carrier: carrier.toLowerCase()
          });
        }
      });
    });
    onChange(newMatrix);
  };

  return (
    <Card 
      title={
        <Space>
          <DollarOutlined style={{ color: '#1890ff' }} />
          <span>리베이트 매트릭스 - {carrier} 번호이동</span>
        </Space>
      }
      className="matrix-rebate-editor"
      extra={
        <Space>
          <Button 
            type="dashed" 
            size="small" 
            onClick={handleQuickFill}
            disabled={disabled}
            tabIndex={-1}
          >
            예시 데이터 채우기
          </Button>
          <Button 
            type="text" 
            size="small" 
            onClick={handleClearAll}
            disabled={disabled}
            danger
            tabIndex={-1}
          >
            모두 지우기
          </Button>
        </Space>
      }
    >
      <div className="matrix-description">
        <Text type="secondary">
          요금제별 계약기간에 따른 리베이트 금액을 입력하세요. (단위: 원)
        </Text>
      </div>

      <Table
        columns={columns}
        dataSource={dataSource}
        pagination={false}
        size="middle"
        bordered
        className="rebate-matrix-table"
        scroll={{ x: 600 }}
      />

      <div className="matrix-summary" style={{ marginTop: 16 }}>
        <Text type="secondary">
          💡 <strong>입력 팁:</strong> 천 단위 구분자는 자동으로 표시됩니다. 
          예: 40000 입력 시 "40,000"으로 표시
        </Text>
      </div>

      {/* 요금제 추가 모달 */}
      <Modal
        title="요금제 추가"
        open={addRowModal}
        onOk={handleAddRow}
        onCancel={() => {
          setAddRowModal(false);
          setNewPlanValue('');
          setNewPlanLabel('');
        }}
        okText="추가"
        cancelText="취소"
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <Text strong>요금제 금액 (원)</Text>
            <InputNumber
              value={newPlanValue}
              onChange={setNewPlanValue}
              style={{ width: '100%', marginTop: 8 }}
              placeholder="예: 110000"
              min={1000}
              step={1000}
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value.replace(/\$\s?|(,*)/g, '')}
            />
          </div>
          <div>
            <Text strong>요금제 라벨</Text>
            <Input
              value={newPlanLabel}
              onChange={(e) => setNewPlanLabel(e.target.value)}
              style={{ marginTop: 8 }}
              placeholder="예: 110K"
            />
          </div>
        </Space>
      </Modal>

      {/* 계약기간 추가 모달 */}
      <Modal
        title="계약기간 추가"
        open={addColumnModal}
        onOk={handleAddColumn}
        onCancel={() => {
          setAddColumnModal(false);
          setNewPeriod('');
        }}
        okText="추가"
        cancelText="취소"
      >
        <div>
          <Text strong>계약기간 (개월)</Text>
          <Select
            value={newPeriod}
            onChange={setNewPeriod}
            style={{ width: '100%', marginTop: 8 }}
            placeholder="계약기간을 선택하세요"
          >
            <Option value="36">36개월</Option>
            <Option value="48">48개월</Option>
            <Option value="60">60개월</Option>
            <Option value="6">6개월</Option>
            <Option value="18">18개월</Option>
          </Select>
          <Text type="secondary" style={{ fontSize: '12px', marginTop: 8, display: 'block' }}>
            일반적이지 않은 기간을 추가하려면 직접 입력하세요:
          </Text>
          <InputNumber
            value={newPeriod}
            onChange={setNewPeriod}
            style={{ width: '100%', marginTop: 4 }}
            placeholder="직접 입력 (예: 30)"
            min={1}
            max={120}
          />
        </div>
      </Modal>
    </Card>
  );
};

export default MatrixRebateEditor;
