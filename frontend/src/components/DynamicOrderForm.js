import React from 'react';
import './DynamicOrderForm.css';

/**
 * 동적 주문서 폼 컴포넌트
 * 정책에 따라 다른 필드를 동적으로 렌더링합니다.
 */
const DynamicOrderForm = ({ policy, formData, onChange, errors, disabled }) => {
    // 정책에 폼 템플릿이 없으면 빈 컴포넌트 반환
    if (!policy || !policy.form_template) {
        return null;
    }

    const renderField = (field) => {
        const value = formData[field.name] || '';
        const error = errors[field.name];

        switch (field.type) {
            case 'text':
                return (
                    <div key={field.name} className="form-group">
                        <label>
                            {field.label}
                            {field.required && ' *'}
                        </label>
                        <input
                            type="text"
                            name={field.name}
                            value={value}
                            onChange={(e) => onChange(field.name, e.target.value)}
                            disabled={disabled}
                            placeholder={field.placeholder}
                            required={field.required}
                        />
                        {error && <span className="error">{error}</span>}
                        {field.help_text && <span className="help-text">{field.help_text}</span>}
                    </div>
                );

            case 'number':
                return (
                    <div key={field.name} className="form-group">
                        <label>
                            {field.label}
                            {field.required && ' *'}
                        </label>
                        <input
                            type="number"
                            name={field.name}
                            value={value}
                            onChange={(e) => onChange(field.name, e.target.value)}
                            disabled={disabled}
                            placeholder={field.placeholder}
                            required={field.required}
                            min={field.min}
                            max={field.max}
                        />
                        {error && <span className="error">{error}</span>}
                        {field.help_text && <span className="help-text">{field.help_text}</span>}
                    </div>
                );

            case 'email':
                return (
                    <div key={field.name} className="form-group">
                        <label>
                            {field.label}
                            {field.required && ' *'}
                        </label>
                        <input
                            type="email"
                            name={field.name}
                            value={value}
                            onChange={(e) => onChange(field.name, e.target.value)}
                            disabled={disabled}
                            placeholder={field.placeholder}
                            required={field.required}
                        />
                        {error && <span className="error">{error}</span>}
                        {field.help_text && <span className="help-text">{field.help_text}</span>}
                    </div>
                );

            case 'tel':
                return (
                    <div key={field.name} className="form-group">
                        <label>
                            {field.label}
                            {field.required && ' *'}
                        </label>
                        <input
                            type="tel"
                            name={field.name}
                            value={value}
                            onChange={(e) => onChange(field.name, e.target.value)}
                            disabled={disabled}
                            placeholder={field.placeholder || '010-0000-0000'}
                            required={field.required}
                            pattern={field.pattern}
                        />
                        {error && <span className="error">{error}</span>}
                        {field.help_text && <span className="help-text">{field.help_text}</span>}
                    </div>
                );

            case 'select':
                return (
                    <div key={field.name} className="form-group">
                        <label>
                            {field.label}
                            {field.required && ' *'}
                        </label>
                        <select
                            name={field.name}
                            value={value}
                            onChange={(e) => onChange(field.name, e.target.value)}
                            disabled={disabled}
                            required={field.required}
                        >
                            <option value="">선택하세요</option>
                            {field.options && field.options.map(option => (
                                <option key={option.value} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                        {error && <span className="error">{error}</span>}
                        {field.help_text && <span className="help-text">{field.help_text}</span>}
                    </div>
                );

            case 'radio':
                return (
                    <div key={field.name} className="form-group">
                        <label>{field.label}{field.required && ' *'}</label>
                        <div className="radio-group">
                            {field.options && field.options.map(option => (
                                <label key={option.value} className="radio-label">
                                    <input
                                        type="radio"
                                        name={field.name}
                                        value={option.value}
                                        checked={value === option.value}
                                        onChange={(e) => onChange(field.name, e.target.value)}
                                        disabled={disabled}
                                        required={field.required}
                                    />
                                    {option.label}
                                </label>
                            ))}
                        </div>
                        {error && <span className="error">{error}</span>}
                        {field.help_text && <span className="help-text">{field.help_text}</span>}
                    </div>
                );

            case 'checkbox':
                return (
                    <div key={field.name} className="form-group checkbox-group">
                        <label>
                            <input
                                type="checkbox"
                                name={field.name}
                                checked={value === true || value === 'true'}
                                onChange={(e) => onChange(field.name, e.target.checked)}
                                disabled={disabled}
                            />
                            {field.label}
                            {field.required && ' *'}
                        </label>
                        {error && <span className="error">{error}</span>}
                        {field.help_text && <span className="help-text">{field.help_text}</span>}
                    </div>
                );

            case 'textarea':
                return (
                    <div key={field.name} className="form-group">
                        <label>
                            {field.label}
                            {field.required && ' *'}
                        </label>
                        <textarea
                            name={field.name}
                            value={value}
                            onChange={(e) => onChange(field.name, e.target.value)}
                            disabled={disabled}
                            placeholder={field.placeholder}
                            required={field.required}
                            rows={field.rows || 3}
                        />
                        {error && <span className="error">{error}</span>}
                        {field.help_text && <span className="help-text">{field.help_text}</span>}
                    </div>
                );

            case 'date':
                return (
                    <div key={field.name} className="form-group">
                        <label>
                            {field.label}
                            {field.required && ' *'}
                        </label>
                        <input
                            type="date"
                            name={field.name}
                            value={value}
                            onChange={(e) => onChange(field.name, e.target.value)}
                            disabled={disabled}
                            required={field.required}
                            min={field.min}
                            max={field.max}
                        />
                        {error && <span className="error">{error}</span>}
                        {field.help_text && <span className="help-text">{field.help_text}</span>}
                    </div>
                );

            case 'file':
                return (
                    <div key={field.name} className="form-group">
                        <label>
                            {field.label}
                            {field.required && ' *'}
                        </label>
                        <input
                            type="file"
                            name={field.name}
                            onChange={(e) => onChange(field.name, e.target.files[0])}
                            disabled={disabled}
                            required={field.required}
                            accept={field.accept}
                        />
                        {error && <span className="error">{error}</span>}
                        {field.help_text && <span className="help-text">{field.help_text}</span>}
                    </div>
                );

            default:
                return null;
        }
    };

    // 폼 템플릿의 필드들을 렌더링
    const fields = policy.form_template.fields || [];
    
    if (fields.length === 0) {
        return null;
    }

    return (
        <div className="dynamic-order-form">
            <h4>추가 정보</h4>
            <div className="dynamic-fields">
                {fields.map(field => renderField(field))}
            </div>
        </div>
    );
};

export default DynamicOrderForm;
