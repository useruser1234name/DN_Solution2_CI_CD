import React from 'react';
import { Card, Row, Col, Divider } from 'antd';
import { DollarOutlined } from '@ant-design/icons';
import DynamicOrderField from '../DynamicOrderField';

const PaymentSupportSection = ({ fields, form, dependencies }) => {
  // 결제 및 지원금 관련 필드들
  const paymentFields = fields.filter(field => 
    ['payment_method', 'installment_months'].includes(field.field_name)
  );
  
  const supportFields = fields.filter(field => 
    ['common_support', 'additional_support', 'free_amount', 'installment_principal', 'additional_fee'].includes(field.field_name)
  );

  if (paymentFields.length === 0 && supportFields.length === 0) return null;

  return (
    <Card 
      title={
        <span>
          <DollarOutlined style={{ marginRight: 8, color: '#fa8c16' }} />
          결제 및 지원금 정보
        </span>
      }
      className="form-section payment-section"
      headStyle={{ 
        background: 'linear-gradient(135deg, #fa8c16 0%, #d46b08 100%)',
        color: 'white'
      }}
    >
      {/* 결제 정보 */}
      {paymentFields.length > 0 && (
        <>
          <div className="subsection-title" style={{ 
            fontSize: '16px', 
            fontWeight: 600, 
            marginBottom: 16,
            color: '#fa8c16'
          }}>
            💳 결제 정보
          </div>
          <Row gutter={[16, 16]}>
            {paymentFields.map(field => (
              <Col xs={24} sm={12} key={field.field_name}>
                <DynamicOrderField
                  field={field}
                  form={form}
                  dependencies={dependencies}
                />
              </Col>
            ))}
          </Row>
        </>
      )}

      {/* 지원금 정보 */}
      {supportFields.length > 0 && (
        <>
          <Divider />
          <div className="subsection-title" style={{ 
            fontSize: '16px', 
            fontWeight: 600, 
            marginBottom: 16,
            color: '#fa8c16'
          }}>
            💰 지원금 정보
          </div>
          <Row gutter={[16, 16]}>
            {supportFields.map(field => (
              <Col xs={24} sm={12} key={field.field_name}>
                <DynamicOrderField
                  field={field}
                  form={form}
                  dependencies={dependencies}
                />
              </Col>
            ))}
          </Row>
        </>
      )}

      {/* 지원금 계산 도움말 */}
      <div className="support-notice" style={{
        marginTop: 16,
        padding: 12,
        background: '#fff7e6',
        border: '1px solid #ffd591',
        borderRadius: 6,
        fontSize: '13px',
        color: '#d46b08'
      }}>
        💡 <strong>지원금 안내:</strong> 공통지원금은 기본 지원금액이며, 추가지원금은 특별 프로모션 금액입니다. 
        프리금액은 고객이 실제 지불하지 않는 금액을 의미합니다.
      </div>
    </Card>
  );
};

export default PaymentSupportSection;
