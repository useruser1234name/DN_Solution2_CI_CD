import React from 'react';
import { Card, Row, Col } from 'antd';
import { SafetyOutlined } from '@ant-design/icons';
import DynamicOrderField from '../DynamicOrderField';

const AdditionalServiceSection = ({ fields, form, dependencies }) => {
  // 부가 서비스 관련 필드들
  const additionalFields = fields.filter(field => 
    ['course', 'insurance', 'welfare', 'legal_info', 'foreigner_info'].includes(field.field_name)
  );

  if (additionalFields.length === 0) return null;

  return (
    <Card 
      title={
        <span>
          <SafetyOutlined style={{ marginRight: 8, color: '#722ed1' }} />
          부가 서비스 정보
        </span>
      }
      className="form-section additional-section"
      headStyle={{ 
        background: 'linear-gradient(135deg, #722ed1 0%, #531dab 100%)',
        color: 'white'
      }}
    >
      <Row gutter={[16, 16]}>
        {additionalFields.map(field => {
          // 텍스트 영역 필드는 전체 너비 사용
          const isTextArea = ['legal_info', 'foreigner_info', 'welfare'].includes(field.field_name);
          
          return (
            <Col xs={24} sm={isTextArea ? 24 : 12} key={field.field_name}>
              <DynamicOrderField
                field={field}
                form={form}
                dependencies={dependencies}
              />
            </Col>
          );
        })}
      </Row>

      {/* 부가 서비스 안내 */}
      <div className="additional-notice" style={{
        marginTop: 16,
        padding: 12,
        background: '#f9f0ff',
        border: '1px solid #d3adf7',
        borderRadius: 6,
        fontSize: '13px',
        color: '#722ed1'
      }}>
        💡 <strong>부가 서비스 안내:</strong> 보험은 기기 보호를 위한 선택 사항이며, 
        법대정보와 외국인정보는 해당하는 경우에만 입력하시면 됩니다.
      </div>
    </Card>
  );
};

export default AdditionalServiceSection;
