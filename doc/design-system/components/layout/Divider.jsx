/**
 * Divider component - visual separator
 */

export function Divider({
  orientation = 'horizontal',
  style = {},
  className = '',
  ...props
}) {
  const baseStyles = {
    backgroundColor: 'var(--border-light)',
  };

  const orientationStyles = {
    horizontal: {
      height: '1px',
      width: '100%',
    },
    vertical: {
      width: '1px',
      height: '100%',
    },
  };

  const finalStyle = {
    ...baseStyles,
    ...orientationStyles[orientation],
    ...style,
  };

  return (
    <div
      className={className}
      style={finalStyle}
      {...props}
    />
  );
}
