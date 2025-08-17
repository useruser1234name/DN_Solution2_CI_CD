/**
 * 리베이트 설정 모달
 * 계층별 리베이트 설정 UI (본사 → 협력사 → 판매점)
 */

import React, { useState, useEffect } from 'react';
import { 
  Table, 
  InputNumber, 
  Button, 
  message, 
  Card, 
  Descriptions,
  Tag,
  Space,
  Alert,
  Tabs,
  Form,
  Switch,
  Divider,
  Typography,
  Tooltip,
  Progress
} from 'antd';
import { 
  DollarOutlined,
  InfoCircleOutlined,
  CalculatorOutlined,
  SaveOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import CustomModal from '../common/CustomModal';
import { policyAPI, handleAPIError } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import './RebateEditModal.css';

const { TabPane } = Tabs;
const { Text, Title } = Typography;

const RebateEditModal = ({ 
  open, 
  onCancel, 
  onSuccess, 
  policyId, 
  policyTitle 
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [rebateMatrix, setRebateMatrix] = useState([]);
  const [editedMatrix, setEditedMatrix] = useState([]);
  const [activeTab, setActiveTab] = useState('matrix');
  
  const { user, hasPermission, isHeadquarters, isAgency } = useAuth();

  // 통신사 옵션
  const carriers = [
    { value: 'skt', label: 'SKT', color: '#ff4d4f' },
    { value: 'kt', label: 'KT', color: '#1890ff' },
    { value: 'lg', label: 'LG U+', color: '#52c41a' },
  ];

  // 요금제 구간 옵션
  const planRanges = [
    { value: 30000, label: '3만원대' },
    { value: 50000, label: '5만원대' },
    { value: 70000, label: '7만원대' },
    { value: 100000, label: '10만원대' },
  ];

  // 계약기간 옵션
  const contractPeriods = [
    { value: 3, label: '3개월' },
    { value: 6, label: '6개월' },
    { value: 9, label: '9개월' },
    { value: 12, label: '12개월' },
    { value: 24, label: '24개월' },
    { value: 36, label: '36개월' },
  ];

  useEffect(() => {
    if (open && policyId) {
      loadRebateMatrix();
    }
  }, [open, policyId]);

  // 리베이트 매트릭스 로드
  const loadRebateMatrix = async () => {
    setLoading(true);
    try {
      const response = await policyAPI.getRebateMatrix(policyId);
      setRebateMatrix(response || []);
      setEditedMatrix(response || []);
    } catch (error) {
      console.error('리베이트 매트릭스 로드 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoading(false);
    }
  };

  // 리베이트 매트릭스 저장
  const handleSave = async () => {
    setSaving(true);
    try {
      await policyAPI.updateRebateMatrix(policyId, {
        matrix_items: editedMatrix.map(item => ({
          carrier: item.carrier,
          plan_range: item.plan_range,
          contract_period: item.contract_period,
          rebate_amount: item.rebate_amount,
        })),
      });
      
      message.success('리베이트 매트릭스가 저장되었습니다.');
      onSuccess?.();
      onCancel();
      
    } catch (error) {
      console.error('리베이트 매트릭스 저장 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setSaving(false);
    }
  };

  // 리베이트 값 변경
  const handleRebateChange = (index, value) => {
    const newMatrix = [...editedMatrix];
    newMatrix[index] = { ...newMatrix[index], rebate_amount: value || 0 };
    setEditedMatrix(newMatrix);
  };

  // 통신사별 색상 가져오기
  const getCarrierColor = (carrier) => {
    const carrierObj = carriers.find(c => c.value === carrier);
    return carrierObj?.color || '#1890ff';
  };

  // 통신사별 라벨 가져오기
  const getCarrierLabel = (carrier) => {
    const carrierObj = carriers.find(c => c.value === carrier);
    return carrierObj?.label || carrier;
  };

  // 요금제 구간 라벨 가져오기
  const getPlanRangeLabel = (planRange) => {
    const planObj = planRanges.find(p => p.value === planRange);
    return planObj?.label || `${planRange.toLocaleString()}원`;
  };

  // 테이블 컬럼 정의
  const columns = [
    {
      title: '통신사',
      dataIndex: 'carrier',
      key: 'carrier',
      width: 80,
      render: (carrier) => (
        <Tag color={getCarrierColor(carrier)}>
          {getCarrierLabel(carrier)}
        </Tag>
      ),
    },
    {
      title: '요금제',
      dataIndex: 'plan_range',
      key: 'plan_range',
      width: 100,
      render: (planRange) => getPlanRangeLabel(planRange),
    },
    {
      title: '계약기간',
      dataIndex: 'contract_period',
      key: 'contract_period',
      width: 80,
      render: (period) => `${period}개월`,
    },
    {
      title: (
        <div>
          총 리베이트
          <Tooltip title="고객이 받는 전체 리베이트 금액">
            <InfoCircleOutlined style={{ marginLeft: 4, color: '#8c8c8c' }} />
          </Tooltip>
        </div>
      ),
      dataIndex: 'rebate_amount',
      key: 'rebate_amount',
      width: 150,
      render: (amount, record, index) => (
        <InputNumber
          value={amount}
          onChange={(value) => handleRebateChange(index, value)}
          formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          parser={value => value.replace(/\$\s?|(,*)/g, '')}
          style={{ width: '100%' }}
          min={0}
          max={1000000}
          step={1000}
          suffix="원"
          disabled={!isHeadquarters() || !hasPermission('rebate.edit_base')}
        />
      ),
    },
  ];

  // 본사용 컬럼 (계층별 분배 표시)
  if (isHeadquarters()) {
    columns.push(
      {
        title: (
          <div>
            협력사 리베이트
            <Tooltip title="협력사가 받는 리베이트 (총 리베이트의 70%)">
              <InfoCircleOutlined style={{ marginLeft: 4, color: '#8c8c8c' }} />
            </Tooltip>
          </div>
        ),
        key: 'agency_rebate',
        width: 120,
        render: (_, record) => {
          const agencyRebate = Math.floor(record.rebate_amount * 0.7);
          return (
            <div>
              <Text strong>{agencyRebate.toLocaleString()}원</Text>
              <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                (70%)
              </div>
            </div>
          );
        },
      },
      {
        title: (
          <div>
            판매점 기본
            <Tooltip title="판매점이 받는 기본 리베이트 (총 리베이트의 50%)">
              <InfoCircleOutlined style={{ marginLeft: 4, color: '#8c8c8c' }} />
            </Tooltip>
          </div>
        ),
        key: 'retail_rebate',
        width: 120,
        render: (_, record) => {
          const retailRebate = Math.floor(record.rebate_amount * 0.5);
          return (
            <div>
              <Text>{retailRebate.toLocaleString()}원</Text>
              <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                (50%)
              </div>
            </div>
          );
        },
      },
      {
        title: (
          <div>
            본사 수익
            <Tooltip title="본사가 가져가는 수익">
              <InfoCircleOutlined style={{ marginLeft: 4, color: '#8c8c8c' }} />
            </Tooltip>
          </div>
        ),
        key: 'hq_profit',
        width: 120,
        render: (_, record) => {
          const agencyRebate = Math.floor(record.rebate_amount * 0.7);
          const hqProfit = record.rebate_amount - agencyRebate;
          const percentage = record.rebate_amount > 0 ? (hqProfit / record.rebate_amount * 100) : 0;
          
          return (
            <div>
              <Text type="secondary">{hqProfit.toLocaleString()}원</Text>
              <div style={{ fontSize: 11, color: '#8c8c8c' }}>
                ({percentage.toFixed(0)}%)
              </div>
            </div>
          );
        },
      }
    );
  }

  // 리베이트 분배 시각화
  const renderRebateDistribution = () => {
    if (editedMatrix.length === 0) return null;

    const sampleRebate = editedMatrix[0]?.rebate_amount || 100000;
    const agencyRebate = Math.floor(sampleRebate * 0.7);
    const retailRebate = Math.floor(sampleRebate * 0.5);
    const hqProfit = sampleRebate - agencyRebate;
    const agencyProfit = agencyRebate - retailRebate;

    return (
      <Card title="리베이트 분배 구조" size="small">
        <div className="rebate-flow">
          <div className="flow-item">
            <div className="flow-box hq">
              <Title level={5}>본사</Title>
              <Text strong>{hqProfit.toLocaleString()}원</Text>
              <Progress 
                percent={hqProfit / sampleRebate * 100} 
                showInfo={false} 
                strokeColor="#ff4d4f"
                size="small"
              />
            </div>
            <div className="flow-arrow">↓</div>
          </div>
          
          <div className="flow-item">
            <div className="flow-box agency">
              <Title level={5}>협력사</Title>
              <Text strong>{agencyProfit.toLocaleString()}원</Text>
              <Text type="secondary" style={{ fontSize: 11 }}>
                (받는 금액: {agencyRebate.toLocaleString()}원)
              </Text>
              <Progress 
                percent={agencyProfit / sampleRebate * 100} 
                showInfo={false} 
                strokeColor="#1890ff"
                size="small"
              />
            </div>
            <div className="flow-arrow">↓</div>
          </div>
          
          <div className="flow-item">
            <div className="flow-box retail">
              <Title level={5}>판매점</Title>
              <Text strong>{retailRebate.toLocaleString()}원</Text>
              <Progress 
                percent={retailRebate / sampleRebate * 100} 
                showInfo={false} 
                strokeColor="#52c41a"
                size="small"
              />
            </div>
          </div>
        </div>
        
        <Alert
          message="리베이트 분배 안내"
          description={`총 리베이트 ${sampleRebate.toLocaleString()}원 기준으로 본사 ${((hqProfit/sampleRebate)*100).toFixed(0)}%, 협력사 ${((agencyProfit/sampleRebate)*100).toFixed(0)}%, 판매점 ${((retailRebate/sampleRebate)*100).toFixed(0)}%로 분배됩니다.`}
          type="info"
          showIcon
          style={{ marginTop: 16 }}
        />
      </Card>
    );
  };

  const handleCancel = () => {
    setEditedMatrix(rebateMatrix); // 변경사항 되돌리기
    onCancel();
  };

  return (
    <CustomModal
      title={
        <div>
          <DollarOutlined style={{ marginRight: 8 }} />
          리베이트 설정 - {policyTitle}
        </div>
      }
      open={open}
      onCancel={handleCancel}
      onOk={handleSave}
      loading={saving}
      width={1200}
      okText="저장"
      cancelText="취소"
      okButtonProps={{
        disabled: !hasPermission('rebate.edit_base') && !hasPermission('rebate.edit_custom'),
      }}
      className="rebate-edit-modal"
    >
      <div className="rebate-content">
        {/* 권한 안내 */}
        {!isHeadquarters() && (
          <Alert
            message="권한 안내"
            description={
              isAgency() 
                ? "협력사는 자신의 판매점에 대한 개별 리베이트만 설정할 수 있습니다."
                : "판매점은 리베이트를 조회만 할 수 있습니다."
            }
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* 리베이트 매트릭스 탭 */}
          <TabPane 
            tab={
              <span>
                <CalculatorOutlined />
                리베이트 매트릭스
              </span>
            } 
            key="matrix"
          >
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Button 
                  icon={<ReloadOutlined />} 
                  onClick={loadRebateMatrix}
                  loading={loading}
                >
                  새로고침
                </Button>
                
                {isHeadquarters() && (
                  <Button 
                    type="dashed"
                    onClick={() => {
                      // 기본 매트릭스 생성
                      const defaultMatrix = [];
                      carriers.forEach(carrier => {
                        planRanges.forEach(plan => {
                          contractPeriods.forEach(period => {
                            defaultMatrix.push({
                              carrier: carrier.value,
                              plan_range: plan.value,
                              contract_period: period.value,
                              rebate_amount: 50000, // 기본값
                            });
                          });
                        });
                      });
                      setEditedMatrix(defaultMatrix);
                      message.success('기본 매트릭스가 생성되었습니다.');
                    }}
                  >
                    기본 매트릭스 생성
                  </Button>
                )}
              </Space>
            </div>

            <Table
              columns={columns}
              dataSource={editedMatrix}
              loading={loading}
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) => 
                  `${range[0]}-${range[1]} / 총 ${total}개`,
              }}
              rowKey={(record) => 
                `${record.carrier}-${record.plan_range}-${record.contract_period}`
              }
              size="small"
              scroll={{ x: 800 }}
              locale={{
                emptyText: (
                  <div style={{ padding: 40 }}>
                    <DollarOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
                    <p>리베이트 매트릭스가 설정되지 않았습니다.</p>
                    {isHeadquarters() && (
                      <Button type="primary" onClick={() => message.info('기본 매트릭스 생성 버튼을 클릭하세요.')}>
                        매트릭스 생성
                      </Button>
                    )}
                  </div>
                ),
              }}
            />
          </TabPane>

          {/* 분배 구조 탭 */}
          <TabPane 
            tab={
              <span>
                <InfoCircleOutlined />
                분배 구조
              </span>
            } 
            key="distribution"
          >
            {renderRebateDistribution()}
            
            <Card title="리베이트 정책 안내" style={{ marginTop: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label="총 리베이트">
                  고객이 받는 전체 혜택 금액
                </Descriptions.Item>
                <Descriptions.Item label="본사 (30%)">
                  총 리베이트에서 협력사 리베이트를 제외한 나머지
                </Descriptions.Item>
                <Descriptions.Item label="협력사 (20%)">
                  총 리베이트의 70%에서 판매점 리베이트를 제외한 나머지
                </Descriptions.Item>
                <Descriptions.Item label="판매점 (50%)">
                  총 리베이트의 50% (기본값, 협력사가 개별 조정 가능)
                </Descriptions.Item>
              </Descriptions>
              
              <Alert
                message="중요 안내"
                description="협력사는 자신의 판매점에 대해서만 개별 리베이트 비율을 조정할 수 있습니다. 본사가 설정한 총 리베이트 금액과 협력사 리베이트는 변경할 수 없습니다."
                type="warning"
                showIcon
                style={{ marginTop: 16 }}
              />
            </Card>
          </TabPane>
        </Tabs>
      </div>
    </CustomModal>
  );
};

export default RebateEditModal;


