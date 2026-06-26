/**
 * Badge component - small label/tag
 */

export function Badge({
  children,
  variant = 'default',
  size = 'md',
  style = {},
  className = '',
  ...props
}) {
  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'var(--font-body)',
    fontWeight: 'var(--font-weight-semibold)',
    borderRadius: 'var(--radius-full)',
    whiteSpace: 'nowrap',
    textTransform: 'capitalize',
  };

  const sizeStyles = {
    sm: {
      padding: '4px 8px',
      fontSize: '11px',
    },
    md: {
      padding: '6px 12px',
      fontSize: '12px',
    },
    lg: {
      padding: '8px 16px',
      fontSize: '13px',
    },
  };

  const variantStyles = {
    default: {
      backgroundColor: 'var(--color-stone)',
      color: 'var(--text-primary)',
    },
    success: {
      backgroundColor: 'var(--color-sage)',
      color: 'white',
    },
    warning: {
      backgroundColor: 'var(--color-warning)',
      color: 'white',
    },
    error: {
      backgroundColor: 'var(--color-error)',
      color: 'white',
    },
    accent: {
      backgroundColor: 'var(--color-clay)',
      color: 'white',
    },
  };

  const finalStyle = {
    ...baseStyles,
    ...sizeStyles[size],
    ...variantStyles[variant],
    ...style,
  };

  return (
    <span
      className={className}
      style={finalStyle}
      {...props}
    >
      {children}
    </span>
  );
}
