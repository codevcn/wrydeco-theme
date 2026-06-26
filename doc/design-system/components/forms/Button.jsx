/**
 * Button component - primary action element
 * 
 * Usage:
 * ```jsx
 * <Button variant="primary" size="md" disabled={false}>
 *   Click me
 * </Button>
 * ```
 * 
 * Variants: primary, secondary, ghost
 * Sizes: sm, md, lg
 * 
 * @startingPoint section="UI Primitives" subtitle="Primary action button" viewport="300x60"
 */

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  className = '',
  style = {},
  type = 'button',
  ...props
}) {
  const baseStyles = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontFamily: 'var(--font-body)',
    fontWeight: 'var(--font-weight-semibold)',
    border: 'none',
    borderRadius: 'var(--radius-sm)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all var(--duration-short) var(--ease-standard)',
    outline: 'none',
  };

  const sizeStyles = {
    sm: {
      padding: '8px 16px',
      fontSize: '12px',
      minHeight: '32px',
    },
    md: {
      padding: '12px 20px',
      fontSize: '14px',
      minHeight: '40px',
    },
    lg: {
      padding: '16px 28px',
      fontSize: '16px',
      minHeight: '48px',
    },
  };

  const variantStyles = {
    primary: {
      backgroundColor: disabled ? 'var(--color-stone)' : 'var(--color-ebony)',
      color: disabled ? 'var(--color-linen)' : 'white',
    },
    secondary: {
      backgroundColor: disabled ? 'var(--color-stone)' : 'var(--color-stone)',
      color: disabled ? 'var(--color-linen)' : 'var(--color-ebony)',
    },
    ghost: {
      backgroundColor: 'transparent',
      color: disabled ? 'var(--color-linen)' : 'var(--color-ebony)',
      border: `1px solid ${disabled ? 'var(--color-stone)' : 'var(--color-linen)'}`,
    },
  };

  const hoverStyles = !disabled && {
    primary: {
      backgroundColor: 'var(--color-bark)',
      boxShadow: 'var(--shadow-card-hover)',
    },
    secondary: {
      backgroundColor: 'var(--color-linen)',
    },
    ghost: {
      borderColor: 'var(--color-bark)',
      color: 'var(--color-bark)',
    },
  };

  const finalStyle = {
    ...baseStyles,
    ...sizeStyles[size],
    ...variantStyles[variant],
    ...style,
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={className}
      style={finalStyle}
      onMouseEnter={(e) => {
        if (!disabled && hoverStyles[variant]) {
          Object.assign(e.target.style, hoverStyles[variant]);
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled) {
          e.target.style.boxShadow = '';
          e.target.style.backgroundColor = variantStyles[variant].backgroundColor;
          e.target.style.borderColor = variantStyles[variant].borderColor || '';
          e.target.style.color = variantStyles[variant].color;
        }
      }}
      onFocus={(e) => {
        e.target.style.outline = '2px solid var(--color-sage)';
        e.target.style.outlineOffset = '2px';
      }}
      onBlur={(e) => {
        e.target.style.outline = 'none';
      }}
      {...props}
    >
      {children}
    </button>
  );
}
