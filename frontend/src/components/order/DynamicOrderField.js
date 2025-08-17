import React, { useState, useEffect } from 'react';
import { 
  Form, 
  Input, 
  Select, 
  DatePicker, 
  InputNumber,
  Radio,
  Checkbox,
  Spin
} from 'antd';
import { get } from '../../services/api';

const { Option } = Select;
const { TextArea } = Input;

const DynamicOrderField = ({ field, form, dependencies = {} }) => {
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(false);

  // 동적 옵션 로드
  useEffect(() => {
    console.log(`[DynamicOrderField] ${field.field_name} 필드 옵션 초기화:`, {
      field_type: field.field_type,
      field_options: field.field_options,
      dependencies
    });
    
    if (field.field_options?.dynamic) {
      loadDynamicOptions();
    } else if (field.field_options?.choices) {
      setOptions(field.field_options.choices);
    } else {
      // 기본 옵션 설정
      setOptions(getDefaultOptionsForFieldType(field.field_type));
    }
  }, [field, dependencies]);

  const getDefaultOptionsForFieldType = (fieldType) => {
    const defaultOptions = {
      'join_type': [
        { value: 'device_change', label: '기변' },
        { value: 'new_subscription', label: '신규' },
        { value: 'number_transfer', label: '번호이동' }
      ],
      'payment_method': [
        { value: 'cash', label: '현금' },
        { value: 'installment', label: '할부' }
      ],
      'sim_type': [
        { value: 'prepaid', label: '선불 (+7,700원)' },
        { value: 'postpaid', label: '후불 (-7,700원)' },
        { value: 'esim', label: '이심' },
        { value: 'reuse', label: '재사용' }
      ],
      'contract_period': [
        { value: '12', label: '12개월' },
        { value: '24', label: '24개월' },
        { value: '36', label: '36개월' }
      ],
      'installment_months': [
        { value: '12', label: '12개월' },
        { value: '24', label: '24개월' },
        { value: '36', label: '36개월' }
      ],
      'insurance': [
        { value: 'damage', label: '파손' },
        { value: 'theft', label: '도난' },
        { value: 'comprehensive', label: '종합' },
        { value: 'none', label: '없음' }
      ],
      'course': [
        { value: 'simple', label: '심플' },
        { value: 'standard', label: '스탠다드' },
        { value: 'premium', label: '프리미엄' }
      ]
    };
    
    return defaultOptions[fieldType] || [];
  };

  const loadDynamicOptions = async () => {
    setLoading(true);
    try {
      const source = field.field_options?.source;
      const dependsOn = field.field_options?.depends_on;
      
      // 정책 계약 기간에 따른 할부개월 옵션 처리
      if (field.field_type === 'installment_months' && dependsOn === 'policy_contract_period') {
        console.log(`[DynamicOrderField] 정책 계약기간에 따른 할부개월 옵션 생성:`, dependencies.policy_contract_period);
        
        // 정책의 계약기간에 따라 할부개월 옵션 동적 생성
        const contractPeriod = dependencies.policy_contract_period || 'all';
        let options = [];
        
        if (contractPeriod === 'all' || contractPeriod === '12') {
          options.push({ value: '12', label: '12개월' });
        }
        
        if (contractPeriod === 'all' || contractPeriod === '24') {
          options.push({ value: '24', label: '24개월' });
        }
        
        if (contractPeriod === 'all' || contractPeriod === '36') {
          options.push({ value: '36', label: '36개월' });
        }
        
        // 기본 옵션 추가
        if (options.length === 0) {
          options = [
            { value: '12', label: '12개월' },
            { value: '24', label: '24개월' },
            { value: '36', label: '36개월' }
          ];
        }
        
        setOptions(options);
        setLoading(false);
        return;
      }
      
      let endpoint = '';
      
      switch (source) {
        case 'CarrierPlan':
          endpoint = 'policies/carrier-plans/';
          // 정책 통신사에 맞는 요금제만 필터링
          if (dependencies.policy_carrier) {
            endpoint += `?carrier=${dependencies.policy_carrier}`;
          }
          // 기존 필터링 유지 (혹시 모를 경우를 위해)
          else if (dependencies.carrier) {
            endpoint += `?carrier=${dependencies.carrier}`;
          }
          break;
        case 'DeviceModel':
          endpoint = 'policies/device-models/';
          break;
        case 'DeviceColor':
          endpoint = 'policies/device-colors/';
          if (dependencies.device_model) {
            endpoint += `?model=${dependencies.device_model}`;
          }
          break;
        default:
          return;
      }

      console.log(`[DynamicOrderField] ${field.field_name} 옵션 로드 요청:`, endpoint);
      const response = await get(endpoint);
      console.log(`[DynamicOrderField] ${field.field_name} API 응답:`, response);
      
      if (response.success && response.data) {
        let data = response.data;
        
        // 이중래핑 처리
        if (data.data && typeof data.data === 'object') {
          console.log(`[DynamicOrderField] ${field.field_name} 이중래핑 감지, data.data 사용`);
          data = data.data;
        }
        
        // 페이지네이션 결과 처리
        if (data.results && Array.isArray(data.results)) {
          console.log(`[DynamicOrderField] ${field.field_name} 페이지네이션 결과 사용`);
          data = data.results;
        }
        
        if (Array.isArray(data)) {
          console.log(`[DynamicOrderField] ${field.field_name} 데이터 배열:`, data);
          const formattedOptions = data.map(item => ({
            value: item.id,
            label: getOptionLabel(source, item)
          }));
          console.log(`[DynamicOrderField] ${field.field_name} 포맷된 옵션:`, formattedOptions);
          setOptions(formattedOptions);
        } else {
          console.warn(`[DynamicOrderField] ${field.field_name} 데이터가 배열이 아님:`, data);
        }
      } else {
        console.warn(`[DynamicOrderField] ${field.field_name} 유효한 응답 없음:`, response);
      }
    } catch (error) {
      console.error(`동적 옵션 로드 실패 (${field.field_name}):`, error);
    } finally {
      setLoading(false);
    }
  };

  const getOptionLabel = (source, item) => {
    switch (source) {
      case 'CarrierPlan':
        return `${item.plan_name} (${item.plan_price?.toLocaleString()}원)`;
      case 'DeviceModel':
        return `${item.manufacturer} ${item.model_name}`;
      case 'DeviceColor':
        return item.color_name;
      default:
        return item.name || item.label || item.toString();
    }
  };

  const renderField = () => {
    const commonProps = {
      placeholder: field.placeholder || `${field.field_label}을(를) 입력하세요`,
      disabled: loading
    };

    switch (field.field_type) {
      case 'text':
      case 'phone':
      case 'email':
        return <Input {...commonProps} />;

      case 'number':
      case 'common_support':
      case 'additional_support':
      case 'free_amount':
      case 'installment_principal':
        return (
          <InputNumber 
            {...commonProps}
            style={{ width: '100%' }}
            formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            parser={value => value.replace(/\$\s?|(,*)/g, '')}
            min={0}
          />
        );

      case 'textarea':
      case 'additional_fee':
      case 'welfare':
      case 'legal_info':
      case 'foreigner_info':
        return <TextArea {...commonProps} rows={3} />;

      case 'date':
      case 'birth_date':
        return <DatePicker {...commonProps} style={{ width: '100%' }} placeholder="날짜를 선택하세요" />;

      case 'select':
      case 'join_type':
      case 'sim_type':
      case 'contract_period':
      case 'payment_method':
      case 'installment_months':
      case 'insurance':
      case 'course':
        return (
          <Select {...commonProps} loading={loading}>
            {options.map(option => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        );

      case 'carrier_plan':
        return (
          <Select 
            {...commonProps} 
            loading={loading}
            showSearch
            filterOption={(input, option) =>
              option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
            }
            notFoundContent={loading ? <Spin size="small" /> : (options.length === 0 ? "요금제가 없습니다" : null)}
          >
            {options.length > 0 ? (
              options.map(option => (
                <Option key={option.value} value={option.value}>
                  {option.label}
                </Option>
              ))
            ) : (
              <Option disabled value="no_options">요금제를 불러오는 중...</Option>
            )}
          </Select>
        );

      case 'device_model':
        return (
          <Select 
            {...commonProps} 
            loading={loading}
            showSearch
            filterOption={(input, option) =>
              option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
            }
            onChange={(value) => {
              // 모델 변경 시 색상 초기화
              if (form && field.field_name === 'device_model') {
                form.setFieldsValue({ device_color: null });
              }
            }}
          >
            {options.map(option => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        );

      case 'device_color':
        return (
          <Select 
            {...commonProps} 
            loading={loading}
            disabled={loading || !dependencies.device_model}
            placeholder={!dependencies.device_model ? '먼저 모델을 선택하세요' : commonProps.placeholder}
          >
            {options.map(option => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        );

      case 'radio':
        return (
          <Radio.Group>
            {options.map(option => (
              <Radio key={option.value} value={option.value}>
                {option.label}
              </Radio>
            ))}
          </Radio.Group>
        );

      case 'checkbox':
        return (
          <Checkbox.Group>
            {options.map(option => (
              <Checkbox key={option.value} value={option.value}>
                {option.label}
              </Checkbox>
            ))}
          </Checkbox.Group>
        );

      default:
        return <Input {...commonProps} />;
    }
  };

  const rules = [];
  if (field.is_required) {
    rules.push({
      required: true,
      message: `${field.field_label}은(는) 필수 입력 사항입니다.`
    });
  }

  // 특별한 유효성 검사 규칙
  if (field.field_type === 'email') {
    rules.push({
      type: 'email',
      message: '올바른 이메일 형식을 입력하세요.'
    });
  }

  if (field.field_type === 'phone') {
    rules.push({
      pattern: /^01[0-9]-?[0-9]{4}-?[0-9]{4}$/,
      message: '올바른 전화번호 형식을 입력하세요. (예: 010-1234-5678)'
    });
  }

  return (
    <Form.Item
      name={field.field_name}
      label={field.field_label}
      rules={rules}
      help={field.help_text}
      extra={field.field_type === 'sim_type' && '선불: 본사 7,700원 지급, 후불: 본사 7,700원 차감'}
    >
      {renderField()}
    </Form.Item>
  );
};

export default DynamicOrderField;
