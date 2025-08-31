import React from 'react';
import './ToggleSwitch.css';

const ToggleSwitch = ({ checked, onChange, disabled = false, onColor = '#ced6e0', offColor = '#30336b', onText = 'ON', offText = 'OFF' }) => {
  const handleClick = () => {
    if (disabled) return;
    onChange && onChange(!checked);
  };

  return (
    <div className={`toggle-switch ${disabled ? 'disabled' : ''}`}>
      <span className="toggle-label">{checked ? onText : offText}</span>
      <button
        type="button"
        className={`toggle-button ${checked ? 'on' : ''}`}
        style={{
          '--toggle-active': onColor,
          '--toggle-inactive': offColor,
        }}
        onClick={handleClick}
        aria-pressed={checked}
        aria-label={checked ? 'On' : 'Off'}
      >
        <span className="toggle-knob" />
      </button>
    </div>
  );
};

export default ToggleSwitch;


