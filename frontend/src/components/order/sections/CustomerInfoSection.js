import React from 'react';
import { Card, Row, Col } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import DynamicOrderField from '../DynamicOrderField';

const CustomerInfoSection = ({ fields, form, dependencies }) => {
  // 고객 정보 관련 필드들
  const customerFields = fields.filter(field => 
    ['customer_name', 'join_type', 'birth_date', 'phone_number'].includes(field.field_name)
  );

  if (customerFields.length === 0) return null;

  return (
    <Card 
      title={
        <span>
          <UserOutlined style={{ marginRight: 8, color: '#1890ff' }} />
          고객 정보
        </span>
      }
      className="form-section customer-section"
      headStyle={{ 
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white'
      }}
    >
      <Row gutter={[16, 16]}>
        {customerFields.map(field => (
          <Col xs={24} sm={12} key={field.field_name}>
            <DynamicOrderField
              field={field}
              form={form}
              dependencies={dependencies}
            />
          </Col>
        ))}
      </Row>
    </Card>
  );
};

export default CustomerInfoSection;
