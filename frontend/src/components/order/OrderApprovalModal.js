/**
 * 주문 승인 워크플로우 모달
 * 주문 승인/거부 및 상태 관리
 */

import React, { useState, useEffect } from 'react';
import { 
  Steps, 
  Card, 
  Button, 
  Space, 
  message, 
  Input, 
  Tag, 
  Descriptions,
  Timeline,
  Alert,
  Popconfirm,
  Typography,
  Row,
  Col
} from 'antd';
import { 
  CheckOutlined,
  CloseOutlined,
  EyeOutlined,
  HistoryOutlined,
  UserOutlined,
  CalendarOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import CustomModal from '../common/CustomModal';
import DynamicOrderForm from './DynamicOrderForm';
import { orderAPI, handleAPIError } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import './OrderApprovalModal.css';

const { Step } = Steps;
const { TextArea } = Input;
const { Text, Title } = Typography;

const OrderApprovalModal = ({ 
  open, 
  onCancel, 
  onSuccess, 
  orderId,
  mode = 'approval' // 'approval' | 'view'
}) => {
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [approvalNote, setApprovalNote] = useState('');
  const [rejectionNote, setRejectionNote] = useState('');
  const [activeTab, setActiveTab] = useState('details');
  
  const { user, hasPermission } = useAuth();

  useEffect(() => {
    if (open && orderId) {
      loadOrder();
    }
  }, [open, orderId]);

  // 주문 정보 로드
  const loadOrder = async () => {
    setLoading(true);
    try {
      const response = await orderAPI.getOrder(orderId);
      setOrder(response);
    } catch (error) {
      console.error('주문 정보 로드 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoading(false);
    }
  };

  // 주문 승인
  const handleApprove = async () => {
    setActionLoading(true);
    try {
      await orderAPI.approveOrder(orderId, {
        note: approvalNote,
      });
      message.success('주문이 승인되었습니다.');
      onSuccess?.();
      onCancel();
    } catch (error) {
      console.error('주문 승인 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setActionLoading(false);
    }
  };

  // 주문 거부
  const handleReject = async () => {
    if (!rejectionNote.trim()) {
      message.error('거부 사유를 입력해주세요.');
      return;
    }
    
    setActionLoading(true);
    try {
      await orderAPI.rejectOrder(orderId, rejectionNote);
      message.success('주문이 거부되었습니다.');
      onSuccess?.();
      onCancel();
    } catch (error) {
      console.error('주문 거부 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setActionLoading(false);
    }
  };

  // 주문 상태별 단계 정의
  const getOrderSteps = () => {
    const steps = [
      {
        title: '접수',
        description: '주문서 제출',
        status: order?.status === 'draft' ? 'process' : 'finish',
        icon: <FileTextOutlined />,
      },
      {
        title: '검토',
        description: '내용 검토 중',
        status: order?.status === 'pending' ? 'process' : 
               ['approved', 'processing', 'completed'].includes(order?.status) ? 'finish' : 'wait',
        icon: <EyeOutlined />,
      },
      {
        title: '승인',
        description: '승인/거부 결정',
        status: order?.status === 'approved' ? 'finish' :
               order?.status === 'rejected' ? 'error' :
               order?.status === 'pending' ? 'process' : 'wait',
        icon: order?.status === 'rejected' ? <CloseOutlined /> : <CheckOutlined />,
      },
      {
        title: '처리',
        description: '주문 처리 진행',
        status: ['processing', 'completed'].includes(order?.status) ? 'finish' : 'wait',
        icon: <UserOutlined />,
      },
      {
        title: '완료',
        description: '주문 처리 완료',
        status: order?.status === 'completed' ? 'finish' : 'wait',
        icon: <CheckOutlined />,
      },
    ];

    return steps;
  };

  // 상태별 색상
  const getStatusColor = (status) => {
    const colors = {
      draft: 'default',
      pending: 'processing',
      approved: 'success',
      rejected: 'error',
      processing: 'warning',
      completed: 'success',
    };
    return colors[status] || 'default';
  };

  // 상태별 라벨
  const getStatusLabel = (status) => {
    const labels = {
      draft: '임시저장',
      pending: '승인대기',
      approved: '승인됨',
      rejected: '거부됨',
      processing: '처리중',
      completed: '완료',
    };
    return labels[status] || status;
  };

  const canApprove = hasPermission('order.approve') && order?.status === 'pending';
  const canReject = hasPermission('order.approve') && order?.status === 'pending';

  return (
    <CustomModal
      title={
        <div className="modal-title">
          <FileTextOutlined style={{ marginRight: 8 }} />
          주문 {mode === 'approval' ? '승인' : '상세'} - {order?.order_number}
        </div>
      }
      open={open}
      onCancel={onCancel}
      width={1200}
      customFooter
      footer={
        mode === 'approval' && canApprove ? [
          <Button key="cancel" onClick={onCancel}>
            닫기
          </Button>,
          <Popconfirm
            key="reject"
            title="주문 거부"
            description={
              <div style={{ width: 300 }}>
                <p>주문을 거부하시겠습니까?</p>
                <TextArea
                  placeholder="거부 사유를 입력하세요"
                  value={rejectionNote}
                  onChange={(e) => setRejectionNote(e.target.value)}
                  rows={3}
                  style={{ marginTop: 8 }}
                />
              </div>
            }
            onConfirm={handleReject}
            okText="거부"
            cancelText="취소"
            okType="danger"
          >
            <Button 
              danger 
              icon={<CloseOutlined />}
              loading={actionLoading}
            >
              거부
            </Button>
          </Popconfirm>,
          <Button 
            key="approve"
            type="primary"
            icon={<CheckOutlined />}
            loading={actionLoading}
            onClick={handleApprove}
          >
            승인
          </Button>,
        ] : [
          <Button key="close" onClick={onCancel}>
            닫기
          </Button>,
        ]
      }
      className="order-approval-modal"
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          로딩 중...
        </div>
      ) : order ? (
        <div className="approval-content">
          {/* 주문 상태 진행도 */}
          <Card className="status-card" style={{ marginBottom: 16 }}>
            <Steps current={getOrderSteps().findIndex(step => step.status === 'process')}>
              {getOrderSteps().map((step, index) => (
                <Step 
                  key={index}
                  title={step.title}
                  description={step.description}
                  status={step.status}
                  icon={step.icon}
                />
              ))}
            </Steps>
          </Card>

          <Row gutter={[16, 16]}>
            {/* 좌측: 주문 정보 */}
            <Col xs={24} lg={14}>
              {/* 기본 정보 */}
              <Card title="주문 정보" style={{ marginBottom: 16 }}>
                <Descriptions column={2} size="small">
                  <Descriptions.Item label="주문번호">
                    <Text code>{order.order_number}</Text>
                  </Descriptions.Item>
                  
                  <Descriptions.Item label="상태">
                    <Tag color={getStatusColor(order.status)}>
                      {getStatusLabel(order.status)}
                    </Tag>
                  </Descriptions.Item>
                  
                  <Descriptions.Item label="고객명">
                    {order.customer_name}
                  </Descriptions.Item>
                  
                  <Descriptions.Item label="정책">
                    {order.policy_title}
                  </Descriptions.Item>
                  
                  <Descriptions.Item label="신청자">
                    {order.created_by_username}
                  </Descriptions.Item>
                  
                  <Descriptions.Item label="신청 업체">
                    {order.company_name}
                  </Descriptions.Item>
                  
                  <Descriptions.Item label="신청일시">
                    <CalendarOutlined style={{ marginRight: 4 }} />
                    {new Date(order.created_at).toLocaleString()}
                  </Descriptions.Item>
                  
                  <Descriptions.Item label="수정일시">
                    <CalendarOutlined style={{ marginRight: 4 }} />
                    {new Date(order.updated_at).toLocaleString()}
                  </Descriptions.Item>
                </Descriptions>

                {order.notes && (
                  <div style={{ marginTop: 16 }}>
                    <Text strong>메모:</Text>
                    <div style={{ 
                      marginTop: 8, 
                      padding: 12, 
                      background: '#f5f5f5', 
                      borderRadius: 4,
                      border: '1px solid #f0f0f0'
                    }}>
                      {order.notes}
                    </div>
                  </div>
                )}
              </Card>

              {/* 주문서 내용 */}
              <Card title="주문서 내용">
                <DynamicOrderForm
                  policyId={order.policy}
                  orderId={order.id}
                  readOnly={true}
                />
              </Card>
            </Col>

            {/* 우측: 처리 정보 */}
            <Col xs={24} lg={10}>
              {/* 승인 노트 (승인 모드일 때) */}
              {mode === 'approval' && canApprove && (
                <Card title="승인 처리" style={{ marginBottom: 16 }}>
                  <Alert
                    message="승인 검토"
                    description="주문 내용을 검토하고 승인 여부를 결정하세요."
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  
                  <div style={{ marginBottom: 16 }}>
                    <Text strong>승인 메모 (선택사항):</Text>
                    <TextArea
                      placeholder="승인 관련 메모를 입력하세요"
                      value={approvalNote}
                      onChange={(e) => setApprovalNote(e.target.value)}
                      rows={3}
                      style={{ marginTop: 8 }}
                    />
                  </div>
                </Card>
              )}

              {/* 처리 이력 */}
              <Card 
                title={
                  <div>
                    <HistoryOutlined style={{ marginRight: 8 }} />
                    처리 이력
                  </div>
                }
              >
                <Timeline>
                  <Timeline.Item color="blue">
                    <div>
                      <Text strong>주문 접수</Text>
                      <br />
                      <Text type="secondary">
                        {order.created_by_username} • {new Date(order.created_at).toLocaleString()}
                      </Text>
                    </div>
                  </Timeline.Item>
                  
                  {order.approved_at && (
                    <Timeline.Item color="green">
                      <div>
                        <Text strong>승인됨</Text>
                        <br />
                        <Text type="secondary">
                          {order.approved_by_username} • {new Date(order.approved_at).toLocaleString()}
                        </Text>
                        {order.approval_note && (
                          <div style={{ marginTop: 4, fontSize: 12 }}>
                            메모: {order.approval_note}
                          </div>
                        )}
                      </div>
                    </Timeline.Item>
                  )}
                  
                  {order.rejected_at && (
                    <Timeline.Item color="red">
                      <div>
                        <Text strong>거부됨</Text>
                        <br />
                        <Text type="secondary">
                          {order.rejected_by_username} • {new Date(order.rejected_at).toLocaleString()}
                        </Text>
                        {order.rejection_reason && (
                          <div style={{ 
                            marginTop: 4, 
                            fontSize: 12, 
                            color: '#ff4d4f',
                            background: '#fff2f0',
                            padding: 4,
                            borderRadius: 2
                          }}>
                            사유: {order.rejection_reason}
                          </div>
                        )}
                      </div>
                    </Timeline.Item>
                  )}
                  
                  {order.status === 'pending' && (
                    <Timeline.Item color="gray">
                      <Text type="secondary">승인 대기 중...</Text>
                    </Timeline.Item>
                  )}
                </Timeline>
              </Card>
            </Col>
          </Row>
        </div>
      ) : (
        <div style={{ textAlign: 'center', padding: 40 }}>
          주문 정보를 찾을 수 없습니다.
        </div>
      )}
    </CustomModal>
  );
};

export default OrderApprovalModal;


