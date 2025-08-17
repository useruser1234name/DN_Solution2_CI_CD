import React from 'react';
import { Card, Row, Col } from 'antd';
import { MobileOutlined } from '@ant-design/icons';
import DynamicOrderField from '../DynamicOrderField';

const DeviceCommunicationSection = ({ fields, form, dependencies }) => {
  // 기기 및 통신 관련 필드들
  const deviceCommFields = fields.filter(field => 
    ['device_model', 'device_color', 'serial_number', 'carrier_plan', 'sim_type'].includes(field.field_name)
  );

  if (deviceCommFields.length === 0) return null;

  return (
    <Card 
      title={
        <span>
          <MobileOutlined style={{ marginRight: 8, color: '#52c41a' }} />
          기기 및 통신 정보
        </span>
      }
      className="form-section device-section"
      headStyle={{ 
        background: 'linear-gradient(135deg, #52c41a 0%, #389e0d 100%)',
        color: 'white'
      }}
    >
      <Row gutter={[16, 16]}>
        {deviceCommFields.map(field => (
          <Col xs={24} sm={12} key={field.field_name}>
            <DynamicOrderField
              field={field}
              form={form}
              dependencies={dependencies}
            />
          </Col>
        ))}
      </Row>
      
      {/* 유심비 안내 */}
      <div className="sim-type-notice" style={{
        marginTop: 16,
        padding: 12,
        background: '#f6ffed',
        border: '1px solid #b7eb8f',
        borderRadius: 6,
        fontSize: '13px',
        color: '#52c41a'
      }}>
        💡 <strong>유심비 안내:</strong> 선불 선택 시 본사에서 7,700원 지급, 후불 선택 시 본사에서 7,700원 차감됩니다.
      </div>
    </Card>
  );
};

export default DeviceCommunicationSection;
