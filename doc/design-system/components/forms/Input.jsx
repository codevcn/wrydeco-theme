/**
 * Input component - text input field
 */

export function Input({
  type = 'text',
  placeholder = '',
  value = '',
  onChange = () => {},
  disabled = false,
  error = false,
  style = {},
  className = '',
  ...props
}) {
  const baseStyles = {
    fontFamily: 'var(--font-body)',
    fontSize: 'var(--font-size-body-md)',
    padding: 'var(--input-padding)',
    border: `1px solid ${error ? 'var(--color-error)' : 'var(--border-default)'}`,
    borderRadius: 'var(--radius-sm)',
    backgroundColor: disabled ? 'var(--bg-disabled)' : 'var(--bg-tertiary)',
    color: disabled ? 'var(--text-disabled)' : 'var(--text-primary)',
    cursor: disabled ? 'not-allowed' : 'text',
    transition: 'all var(--duration-short) var(--ease-standard)',
    minHeight: 'var(--input-height)',
    width: '100%',
    outline: 'none',
  };

  const finalStyle = {
    ...baseStyles,
    ...style,
  };

  return (
    <input
      type={type}
      placeholder={placeholder}
      value={value}
      onChange={onChange}
      disabled={disabled}
      className={className}
      style={finalStyle}
      onFocus={(e) => {
        e.target.style.borderColor = 'var(--color-sage)';
        e.target.style.boxShadow = 'var(--shadow-focus)';
      }}
      onBlur={(e) => {
        e.target.style.borderColor = error ? 'var(--color-error)' : 'var(--border-default)';
        e.target.style.boxShadow = 'none';
      }}
      {...props}
    />
  );
}
