/**
 * Card component - elevated content container
 */

export function Card({
  children,
  variant = 'default',
  elevation = 1,
  style = {},
  className = '',
  ...props
}) {
  const baseStyles = {
    backgroundColor: variant === 'elevated' ? 'white' : 'var(--color-cream)',
    borderRadius: 'var(--radius-sm)',
    padding: 'var(--card-padding)',
    transition: 'all var(--duration-short) var(--ease-standard)',
  };

  const elevationStyles = {
    1: { boxShadow: 'var(--shadow-elevation-1)' },
    2: { boxShadow: 'var(--shadow-elevation-2)' },
    3: { boxShadow: 'var(--shadow-elevation-3)' },
    4: { boxShadow: 'var(--shadow-elevation-4)' },
  };

  const finalStyle = {
    ...baseStyles,
    ...elevationStyles[elevation],
    ...style,
  };

  return (
    <div
      className={className}
      style={finalStyle}
      onMouseEnter={(e) => {
        e.target.style.boxShadow = `var(--shadow-elevation-${Math.min(elevation + 1, 4)})`;
      }}
      onMouseLeave={(e) => {
        e.target.style.boxShadow = elevationStyles[elevation].boxShadow;
      }}
      {...props}
    >
      {children}
    </div>
  );
}
